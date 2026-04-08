import hashlib
from typing import List, Dict
from sqlalchemy.exc import IntegrityError
from src.db.models import Transaction, CostTypeEnum
from src.db.connection import SessionLocal
from src.ingestion.validators import RawTransaction

class DatabaseLoader:
    def __init__(self, account_id: str):
        self.account_id = account_id

    def generate_transaction_id(self, tx: RawTransaction) -> str:
        date_str = tx.booking_date.strftime('%Y-%m-%d')
        amount_str = f"{tx.amount:.2f}"
        
        raw_str = f"{date_str}|{amount_str}|{tx.raw_payee}|{self.account_id}"
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()

    def load(self, valid_transactions: List[RawTransaction]) -> dict:
        db = SessionLocal()
        stats = {"total": len(valid_transactions), "inserted": 0, "skipped": 0, "errors": 0}
        
        for tx in valid_transactions:
            tx_id = self.generate_transaction_id(tx)
            
            exists = db.query(Transaction).filter_by(id=tx_id).first()
            if exists:
                stats["skipped"] += 1
                continue
                
            db_tx = Transaction(
                id=tx_id,
                account_id=self.account_id,
                booking_date=tx.booking_date,
                valuta_date=tx.valuta_date,
                amount=tx.amount,
                currency=tx.currency,
                raw_payee=tx.raw_payee[:255],
                raw_purpose=tx.raw_purpose,
                needs_review=True,
                cost_type=CostTypeEnum.unclassified
            )
            try:
                db.add(db_tx)
                db.commit()
                stats["inserted"] += 1
            except IntegrityError:
                db.rollback()
                stats["skipped"] += 1
            except Exception as e:
                db.rollback()
                stats["errors"] += 1
                
        db.close()
        return stats
