import pandas as pd
import streamlit as st
from src.db.connection import SessionLocal
from src.db.models import Transaction, Account

def get_db():
    return SessionLocal()

@st.cache_data(ttl=5)
def load_all(_db):
    """
    Loads raw transactions and accounts from the database.
    Normalizes cost_type for easier processing.
    """
    tx = pd.read_sql(_db.query(Transaction).statement, _db.bind)
    acc = pd.read_sql(_db.query(Account).statement, _db.bind)
    
    if not tx.empty:
        tx["booking_date"] = pd.to_datetime(tx["booking_date"])
        # Normalize cost_type to string for reliable comparisons
        tx["cost_type_str"] = tx["cost_type"].apply(
            lambda x: x.name if hasattr(x, "name") else str(x) if x else "unclassified"
        )
    return tx, acc
