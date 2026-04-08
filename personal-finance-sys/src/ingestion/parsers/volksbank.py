import pandas as pd
import os
from typing import List, Dict, Any
from src.ingestion.base_parser import BaseParser

class VolksbankCSVParser(BaseParser):
    def parse(self, filepath: str) -> List[Dict[str, Any]]:
        try:
            df = pd.read_csv(filepath, sep=';', encoding='cp1252')
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, sep=';', encoding='utf-8')
            
        # Identify columns (Prioritize the first match to avoid duplicates)
        col_mapping = {}
        target_cols = ['booking_date', 'valuta_date', 'raw_payee', 'raw_purpose', 'amount', 'currency']
        found_targets = set()
        
        for col in df.columns:
            col_lower = col.lower()
            target = None
            
            if 'buchungstag' in col_lower and 'booking_date' not in found_targets: 
                target = 'booking_date'
            elif 'valuta' in col_lower and 'valuta_date' not in found_targets: 
                target = 'valuta_date'
            elif any(k in col_lower for k in ['zahlungsbeteiligte', 'auftraggeber', 'empfänger', 'begünstigt']) and 'raw_payee' not in found_targets:
                target = 'raw_payee'
            elif 'verwendungszweck' in col_lower and 'raw_purpose' not in found_targets: 
                target = 'raw_purpose'
            elif ('betrag' in col_lower or 'umsatz' in col_lower) and 'amount' not in found_targets: 
                target = 'amount'
            elif ('währung' in col_lower or 'waehrung' in col_lower) and 'currency' not in found_targets: 
                target = 'currency'
            
            if target:
                col_mapping[col] = target
                found_targets.add(target)
                
        df = df.rename(columns=col_mapping)
        
        required = ['booking_date', 'amount']
        missing = [rt for rt in required if rt not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns from CSV mapping: {missing}")
            
        # Robust amount conversion
        amount_series = df['amount']
        if isinstance(amount_series, pd.DataFrame):
            # If multiple columns were named 'amount', take the first one
            amount_series = amount_series.iloc[:, 0]
            
        if amount_series.dtype == object:
            df['amount'] = df['amount'].astype(str)
            df['amount'] = df['amount'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
            
        df['booking_date'] = pd.to_datetime(df['booking_date'], format='%d.%m.%Y', errors='coerce').dt.date
        if 'valuta_date' in df.columns:
            df['valuta_date'] = pd.to_datetime(df['valuta_date'], format='%d.%m.%Y', errors='coerce').dt.date
        else:
            df['valuta_date'] = None

        filename = os.path.basename(filepath)
        
        records = []
        for _, row in df.iterrows():
            if pd.isna(row['booking_date']) or pd.isna(row['amount']):
                continue
                
            records.append({
                'booking_date': row['booking_date'],
                'valuta_date': row['valuta_date'] if pd.notna(row['valuta_date']) else None,
                'amount': float(row['amount']),
                'currency': row.get('currency', 'EUR') or 'EUR',
                'raw_payee': str(row.get('raw_payee', 'UNKNOWN_PAYEE'))[:255] if pd.notna(row.get('raw_payee')) else "UNKNOWN_PAYEE",
                'raw_purpose': str(row.get('raw_purpose', '')) if pd.notna(row.get('raw_purpose')) else "",
                'source_file': filename
            })
            
        return records
