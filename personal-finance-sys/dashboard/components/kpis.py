import streamlit as st
from dashboard.services.queries import mom_delta

def render_steering_cockpit(m: dict):
    """
    Renders 7 KPI cards across two rows as defined in the steering model.
    """
    # Use st.container to group rows
    with st.container():
        st.markdown("### 🚦 Primary Steering Row")
        k1, k2, k3 = st.columns(3)
        
        k1.metric(
            "Net Surplus (MTD)", 
            f"€{m['inc_mtd'] - m['fixed_mtd'] - m['var_mtd']:,.0f}", 
            delta=mom_delta(m['inc_mtd'] - m['fixed_mtd'] - m['var_mtd'], m['inc_p'] - m['fixed_p'] - m['var_p'])
        )
        
        k2.metric(
            "Savings Rate (Rolling 3M)", 
            f"{m['sr_r3m']:.1f}%",
            help="Income - All Expenses / Income (Smoothed over 3 months)"
        )
        
        k3.metric(
            "Liquid Runway", 
            f"€{m['liquid_runway']:,.0f}",
            help="Total balance across checking & cash accounts"
        )

    st.markdown("---")

    with st.container():
        st.markdown("### 📉 Operational Burn Row")
        k4, k5, k6, k7 = st.columns(4)
        
        k4.metric(
            "Fixed Baseline (MTD)", 
            f"€{m['fixed_mtd']:,.0f}", 
            delta=mom_delta(m['fixed_mtd'], m['fixed_p']),
            delta_color="inverse"
        )
        
        k5.metric(
            "Variable Burn (Last 30d)", 
            f"€{m['var_mtd']:,.0f}", 
            delta=mom_delta(m['var_mtd'], m['var_p']),
            delta_color="inverse",
            help="Lifestyle expenses strictly excluding travel and one-offs"
        )
        
        k6.metric(
            "Net Income (MTD)", 
            f"€{m['inc_mtd']:,.0f}", 
            delta=mom_delta(m['inc_mtd'], m['inc_p'])
        )
        
        k7.metric(
            "Data Clarity", 
            f"{m['data_health']:.1f}%", 
            help="Percentage of transactions categorized. Aim for 100%!"
        )
