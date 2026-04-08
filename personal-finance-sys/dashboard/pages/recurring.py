import streamlit as st
import pandas as pd
from src.db.models import CategorizationRule, CostTypeEnum
from src.engine.rules import RuleEngine

def render(expense_df, db):
    """
    Renders the Recurring Costs / Subscriptions page.
    TODO: Add visualization for 'Renewal Calendar' (upcoming payments).
    """
    st.header("Recurring Obligations")
    
    fixed_df = expense_df[expense_df["cost_type_str"] == "fixed"]
    if fixed_df.empty:
        st.info("No fixed costs identified yet.")
    else:
        st.metric("Total Monthly Commitment", f"€{fixed_df['abs_amount'].sum():,.0f}")
        
        st.subheader("Active Subscriptions & Contracts")
        # TODO: Add 'Cancel' or 'Negotiate' reminder flags
        commit_tbl = fixed_df.groupby("raw_payee").agg(
            Total=("abs_amount", "sum"),
            Count=("id", "count"),
            Last_Charged=("booking_date", "max"),
            Category=("main_category", "first"),
        ).sort_values("Total", ascending=False).reset_index()
        
        st.dataframe(commit_tbl, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🕵️ Subscription Hunter")
    # TODO: Integration with LLM to suggest better plans for detected merchants
    engine = RuleEngine(db)
    freqs = engine.detect_recurring_unknowns()
    # ... logic for freqs buttons ...
