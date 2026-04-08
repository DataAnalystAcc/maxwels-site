import streamlit as st
from dashboard.components import charts

def render(df_core, income_df, expense_df, prev_data, ctx, df_raw):
    """
    Renders the Overview tab content with Steering KPIs.
    """
    st.header("Financial Steering Cockpit")
    
    # 1. Fetch Steering Metrics
    from dashboard.services.queries import get_steering_metrics
    m = get_steering_metrics(df_raw, ctx["start_date"], ctx["max_date"])
    
    # 2. Render Cockpit
    from dashboard.components.kpis import render_steering_cockpit
    render_steering_cockpit(m)
    
    st.markdown("---")
    
    # 2. Charts Row
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("Monthly Cashflow")
        st.plotly_chart(charts.cashflow_bar(df_core), use_container_width=True, key="overview_cashflow_bar")
        
    with c_right:
        st.subheader("Running Balance")
        st.plotly_chart(charts.running_balance(ctx["df_filtered"]), use_container_width=True, key="overview_running_balance")
        
    # 3. Cost Structure
    st.subheader("Monthly Cost Breakdown")
    if not expense_df.empty:
        st.plotly_chart(charts.cost_type_breakdown(expense_df), use_container_width=True, key="overview_cost_breakdown")
    else:
        st.info("No expenses found in the current selection.")
