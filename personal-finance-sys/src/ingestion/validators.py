from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date

class RawTransaction(BaseModel):
    booking_date: date
    valuta_date: Optional[date] = None
    amount: float
    currency: str = "EUR"
    raw_payee: str = Field(default="UNKNOWN_PAYEE")
    raw_purpose: str = ""
    source_file: str = "unknown"

    @field_validator('amount')
    @classmethod
    def check_amount(cls, v: float) -> float:
        return round(v, 2)
