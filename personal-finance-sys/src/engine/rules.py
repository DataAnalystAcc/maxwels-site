import json
import re
import os
import pandas as pd
from sqlalchemy.orm import Session
from src.db.models import Transaction, CategorizationRule, CostTypeEnum
from src.db.connection import SessionLocal

class RuleEngine:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        
    def normalize_payee(self, raw_payee: str) -> str:
        """Strips common payment processor prefixes to extract the real merchant."""
        if not raw_payee:
            return ""
            
        cleaned = raw_payee.upper()
        processors = [
            r'PAYPAL\s*\*?', 
            r'AMZN\s*MKTP\s*[A-Z]{0,2}\*?', 
            r'SUMUP\s*\*?',
            r'IZTLE\s*\*?',
            r'STRIPE\s*\*?'
        ]
        for proc in processors:
            cleaned = re.sub(proc, '', cleaned)
            
        return cleaned.strip()
        
    def load_seed_rules(self, filepath: str):
        if not os.path.exists(filepath):
            return 0
            
        with open(filepath, 'r', encoding='utf-8') as f:
            rules = json.load(f)
            
        added = 0
        for r in rules:
            exists = self.db.query(CategorizationRule).filter_by(
                regex_pattern=r['regex_pattern'], 
                search_field=r['search_field']
            ).first()
            
            if not exists:
                ct_val = r.get('assign_cost_type', 'unclassified')
                try:
                    ct_enum = CostTypeEnum(ct_val)
                except ValueError:
                    ct_enum = CostTypeEnum.unclassified
                    
                rule = CategorizationRule(
                    priority=r.get('priority', 100),
                    regex_pattern=r['regex_pattern'],
                    search_field=r['search_field'],
                    assign_main_category=r.get('assign_main_category'),
                    assign_sub_category=r.get('assign_sub_category'),
                    assign_cost_type=ct_enum,
                    set_house_related=r.get('set_house_related'),
                    set_travel_related=r.get('set_travel_related')
                )
                self.db.add(rule)
                added += 1
                
        self.db.commit()
        return added

    def detect_own_transfers(self):
        """Finds transactions between owned accounts. To be implemented fully querying across accounts."""
        # Stub logic: if you have exact opposite amounts within a 3 day window
        pass

    def categorize_unclassified(self):
        """Waterfall categorization engine."""
        rules = self.db.query(CategorizationRule).order_by(CategorizationRule.priority.asc()).all()
        
        compiled_rules = []
        for r in rules:
            try:
                pattern = re.compile(r.regex_pattern, re.IGNORECASE)
                compiled_rules.append((r, pattern))
            except re.error:
                continue

        unclassified = self.db.query(Transaction).filter(
            Transaction.needs_review == True,
            Transaction.main_category.is_(None)
        ).all()
        
        updated_count = 0
        
        for tx in unclassified:
            matched = False
            
            # 1. Normalize Payee String for matching against cleaned rules
            norm_payee = self.normalize_payee(tx.raw_payee)
            
            # 2. Process Waterfall
            for rule, pattern in compiled_rules:
                target_text = ""
                if rule.search_field == 'raw_payee':
                    target_text = norm_payee if norm_payee else tx.raw_payee or ""
                elif rule.search_field == 'raw_purpose':
                    target_text = tx.raw_purpose or ""
                elif rule.search_field == 'any':
                    target_text = f"{norm_payee or tx.raw_payee or ''} {tx.raw_purpose or ''}"
                
                if pattern.search(target_text):
                    tx.main_category = rule.assign_main_category
                    tx.sub_category = rule.assign_sub_category
                    if rule.assign_cost_type:
                        tx.cost_type = rule.assign_cost_type
                    
                    if rule.set_house_related is not None: tx.is_house_related = rule.set_house_related
                    if rule.set_travel_related is not None: tx.is_travel_related = rule.set_travel_related
                    
                    tx.needs_review = False
                    tx.review_reason = None
                    matched = True
                    break
                    
            if not matched:
                tx.review_reason = 'engine_miss'
                # Flag abnormally large amounts as special automatically
                if abs(tx.amount) > 1500:
                    tx.cost_type = CostTypeEnum.special
                
            updated_count += 1
            
        self.db.commit()
        return updated_count
        
    def detect_recurring_unknowns(self):
        """Uses pandas to find repeating payments that might be forgotten fixed costs."""
        # Query unclassified or variable expenses to see if they look fixed
        df = pd.read_sql(
            self.db.query(Transaction).filter(
                Transaction.cost_type != CostTypeEnum.fixed,
                Transaction.amount < 0
            ).statement, 
            self.db.bind
        )
        
        if df.empty:
            return []
            
        # Group by cleaned raw_payee to find recurring matches
        df['norm_payee'] = df['raw_payee'].apply(self.normalize_payee)
        freq_list = []
        
        for payee, group in df.groupby('norm_payee'):
            if count := len(group) >= 3:
                group = group.sort_values('booking_date')
                intervals = group['booking_date'].diff().dt.days.dropna()
                
                if not intervals.empty:
                    mean_val = intervals.mean()
                    std_val = intervals.std()
                    
                    # If variance is low and interval is ~30 days (monthly) or ~365 (yearly)
                    if (28 <= mean_val <= 32 and std_val < 4) or (360 <= mean_val <= 370 and std_val < 10):
                        freq_list.append({
                            "payee": payee,
                            "count": count,
                            "interval_mean": mean_val,
                            "suggestion": "Convert to Fixed Cost"
                        })
                        
        return freq_list
