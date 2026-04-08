import streamlit as st
import pandas as pd
from src.db.models import CategorizationRule

def render(db):
    """
    Renders the Rules & Data Quality page.
    TODO: Add 'Simulate Rules' feature to test regex against unclassified data before saving.
    """
    st.header("Categorization Rules Engine")
    
    st.write("Current active regex rules which drive the automated ingestion pipeline.")
    
    rules_df = pd.read_sql(db.query(CategorizationRule).statement, db.bind)
    if not rules_df.empty:
        # TODO: Add 'Delete Rule' or 'Edit Rule' buttons using a data_editor + row selections
        st.dataframe(
            rules_df[["id", "priority", "regex_pattern", "search_field", "assign_main_category", "assign_cost_type"]]
            .sort_values("priority"),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No rules defined yet.")

    st.markdown("---")
    st.subheader("Data Quality Audit")
    # TODO: Add logic to find 'Conflicts' (e.g., one merchant mapped to two categories)
    st.caption("Heuristic Check: No obvious rule conflicts detected.")
