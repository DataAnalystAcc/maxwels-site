import streamlit as st
import pandas as pd
from src.db.models import CategorizationRule, CostTypeEnum
from src.engine.rules import RuleEngine

def render(expense_df, db):
    """
    Renders the Commitments (Fixed Costs) tab content.
    """
    fixed_df = expense_df[expense_df["cost_type_str"] == "fixed"]
    
    if fixed_df.empty:
        st.info("No fixed costs identified yet. Categorize transactions or run the rule engine.")
    else:
        st.metric("Total Fixed Commitments (Period)", f"€{fixed_df['abs_amount'].sum():,.0f}")
        st.markdown("---")

        st.subheader("Recurring Payees")
        commit_tbl = fixed_df.groupby("raw_payee").agg(
            Total=("abs_amount", "sum"),
            Count=("id", "count"),
            Last_Charged=("booking_date", "max"),
            Category=("main_category", "first"),
        ).sort_values("Total", ascending=False).reset_index()
        
        # Calculate Avg Monthly (approximation)
        commit_tbl["Avg Monthly"] = (commit_tbl["Total"] / max(1, commit_tbl["Count"].max())).round(2)
        commit_tbl.rename(columns={"raw_payee": "Merchant"}, inplace=True)
        
        st.dataframe(
            commit_tbl[["Merchant", "Category", "Total", "Avg Monthly", "Count", "Last_Charged"]],
            use_container_width=True, hide_index=True
        )

    st.markdown("---")
    st.subheader("🕵️ Subscription Hunter")
    
    engine = RuleEngine(db)
    freqs = engine.detect_recurring_unknowns()
    
    if not freqs:
        st.success("No undiscovered recurring patterns found.")
    else:
        for f in freqs:
            c1, c2 = st.columns([5, 1])
            c1.warning(f"**{f['payee']}** — {f['count']}× billed, ~{f['interval_mean']:.0f} days apart")
            
            if c2.button("Make Fixed", key=f"fix_{f['payee']}"):
                new_rule = CategorizationRule(
                    priority=35, regex_pattern=f["payee"], search_field="raw_payee",
                    assign_main_category="Verträge / Abos", assign_cost_type=CostTypeEnum.fixed,
                )
                db.add(new_rule)
                db.commit()
                st.toast(f"Rule created for {f['payee']}. Re-run categorizer.")
                st.rerun()
