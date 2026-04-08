import streamlit as st
from dashboard.components import charts

def render(df_core):
    """
    Renders the Cashflow analysis page.
    TODO: Add daily burn rate heatmaps and rolling average lines.
    """
    st.header("Cashflow & Liquidity")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Monthly Income vs Expenses")
        st.plotly_chart(charts.cashflow_bar(df_core), use_container_width=True, key="cashflow_page_bar")
        
    with col2:
        # TODO: Implement a rolling 7-day or 30-day burn rate chart here
        st.subheader("Net Cashflow (Delta)")
        cf = df_core.copy()
        cf["month"] = cf["booking_date"].dt.to_period("M").astype(str)
        delta_m = cf.groupby("month")["amount"].sum().reset_index()
        fig = charts.px.bar(delta_m, x="month", y="amount", title="Monthly Surplus/Deficit", 
                            template=charts.PLOTLY_TEMPLATE)
        st.plotly_chart(fig, use_container_width=True, key="cashflow_page_delta")
