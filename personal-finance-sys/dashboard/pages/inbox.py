import streamlit as st
import pandas as pd
from src.db.models import Transaction, CostTypeEnum
from src.engine.rules import RuleEngine
from dashboard.config import CAT_OPTIONS

def render(df_raw, db, load_all_cache):
    """
    Renders the Inbox / Operations tab content.
    """
def render(df_raw, db, load_all_cache):
    """
    Advanced Operations Inbox v2 (Redesign)
    """
    st.header("Financial Operations Inbox")
    
    # 1. Triage Filters
    review_status = st.segmented_control(
        "Triage Category", 
        ["All", "Unclassified", "Large Outliers", "Manual Flags"],
        default="All"
    )
    
    df_review = df_raw[df_raw["needs_review"] == True].copy()
    
    if review_status == "Unclassified":
        df_review = df_review[df_review["main_category"].isna() | (df_review["main_category"] == "Sonstiges / Prüfen")]
    elif review_status == "Large Outliers":
        df_review = df_review[df_review["amount"].abs() > 500] # Placeholder threshold
    elif review_status == "Manual Flags":
        df_review = df_review[df_review["review_reason"] == "USER_FLAGGED"]

    if df_review.empty:
        st.success(f"🎉 Inbox Zero for {review_status}!")
        return

    # 2. Sidebar: Data Quality & Rule Simulation
    with st.sidebar:
        st.markdown("### 🔍 Rule Simulator")
        sim_pattern = st.text_input("Test Regex Pattern", help="Preview matches before saving a rule")
        if sim_pattern:
            matches = df_raw[df_raw["raw_payee"].str.contains(sim_pattern, case=False, na=False)]
            st.info(f"**Found {len(matches)} historical matches.**")
            if not matches.empty:
                st.dataframe(matches[["booking_date", "raw_payee", "amount"]].head(5), hide_index=True)

        st.markdown("---")
        st.markdown("### 📊 Data Quality")
        total = len(df_raw)
        needs = len(df_raw[df_raw["needs_review"] == True])
        coverage = (total - needs) / total * 100
        st.metric("Categorization Coverage", f"{coverage:.1f}%")

    # 3. Batch Editor
    st.markdown(f"**{len(df_review)}** transactions require triage.")
    
    # Add selection column
    df_review["Select"] = False
    
    edit_cols = ["Select", "id", "booking_date", "amount", "raw_payee", "raw_purpose", "main_category", "cost_type_str"]
    disp = df_review[edit_cols].copy()
    disp.rename(columns={"cost_type_str": "cost_type"}, inplace=True)
    
    edited = st.data_editor(
        disp,
        column_config={
            "Select": st.column_config.CheckboxColumn(default=False),
            "id": None,
            "booking_date": st.column_config.DateColumn("Date", disabled=True),
            "amount": st.column_config.NumberColumn("€", disabled=True, format="€%.2f"),
            "raw_payee": st.column_config.TextColumn("Payee", disabled=True),
            "main_category": st.column_config.SelectboxColumn("Category", options=CAT_OPTIONS),
            "cost_type": st.column_config.SelectboxColumn("Type", options=["variable", "fixed", "special"]),
        },
        hide_index=True, use_container_width=True, height=400,
        key="inbox_editor"
    )

    # 4. Action Bar
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        batch_cat = st.selectbox("Apply Category to Selected", ["Keep Existing"] + CAT_OPTIONS)
    with c2:
        batch_type = st.selectbox("Apply Cost Type to Selected", ["Keep Existing", "variable", "fixed", "special"])
    with c3:
        st.markdown("<br>", unsafe_allow_html=True) # Align button
        if st.button("🚀 Process Batch", type="primary"):
            engine = RuleEngine(db)
            from src.db.models import CategorizationRule
            
            # Logic: Iterate through edited rows AND check 'Select' column
            updated_count = 0
            for idx, row in edited.iterrows():
                if row["Select"]:
                    tx_id = row["id"]
                    tx_db = db.query(Transaction).filter_by(id=tx_id).first()
                    
                    target_cat = batch_cat if batch_cat != "Keep Existing" else row["main_category"]
                    target_type = batch_type if batch_type != "Keep Existing" else row["cost_type"]
                    
                    if tx_db:
                        tx_db.main_category = target_cat
                        tx_db.cost_type = CostTypeEnum[target_type]
                        tx_db.needs_review = False
                        updated_count += 1
            
            if updated_count > 0:
                db.commit()
                load_all_cache.clear()
                st.success(f"Successfully processed {updated_count} transactions!")
                st.rerun()

    st.markdown("---")
    st.caption("Tip: Use the Rule Simulator in the sidebar to test regex before creating permanent rules.")
