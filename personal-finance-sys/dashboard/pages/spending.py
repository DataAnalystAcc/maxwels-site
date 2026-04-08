import streamlit as st
from dashboard.components import charts

def render(expense_df):
    """
    Renders the Spending tab content.
    """
    if expense_df.empty:
        st.info("No expenses in the selected timeframe.")
        return
        
    st.subheader("Category Breakdown")
    st.plotly_chart(charts.category_treemap(expense_df), use_container_width=True, key="spending_treemap")
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Top 10 Merchants")
        st.plotly_chart(charts.merchant_bar(expense_df), use_container_width=True, key="spending_merchant_bar")
        
    with col_r:
        st.subheader("Category Trend (Monthly)")
        st.plotly_chart(charts.category_trends(expense_df), use_container_width=True, key="spending_trend_lines")
