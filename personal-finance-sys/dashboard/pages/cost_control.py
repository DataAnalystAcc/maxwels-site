import streamlit as st
import plotly.express as px
import pandas as pd
from dashboard.config import PLOTLY_TEMPLATE, COLORS, CAT_OPTIONS

def render(df_core, income_df, expense_df):
    """
    Detailed Category & Cost-Type Analysis View.
    Focuses on Fixed vs Variable vs Special splits.
    """
    if expense_df.empty:
        st.info("No expense data available for analysis.")
        return

    # 0. DATA HEALTH & STEERABILITY
    total_recs = len(expense_df)
    unclassified_val = len(expense_df[expense_df["cost_type_str"] == "unclassified"])
    health_score = (1 - (unclassified_val / total_recs)) * 100 if total_recs > 0 else 100
    
    col_h1, col_h2, col_h3 = st.columns([1, 1, 2])
    with col_h1:
        st.metric("Data Clarity", f"{health_score:.1f}%", help="Percentage of transactions categorized (Fixed/Var/Special)")
    with col_h2:
        operating_total = expense_df[expense_df["cost_type_str"].isin(["fixed", "variable"])]["abs_amount"].sum()
        st.metric("Operating Spend", f"€{operating_total:,.0f}", help="Fixed + Variable (Your true monthly burn rate)")
    with col_h3:
        st.caption("🔴 Unclassified needs to be 0% for a sharp dashboard. Use the Inbox to fix gray areas.")

    st.markdown("---")

    # 1. THE STEERING BAR: Monthly Cost-Type Evolution
    st.subheader("Monthly Cost-Type Evolution")
    
    # Prepare monthly data
    trend_df = expense_df.copy()
    trend_df["month"] = trend_df["booking_date"].dt.to_period("M").astype(str)
    
    # Pivot for stacking
    pivot_df = trend_df.groupby(["month", "cost_type_str"])["abs_amount"].sum().reset_index()
    
    fig_steering = px.bar(
        pivot_df, x="month", y="abs_amount", color="cost_type_str",
        title="Structural vs Lifestyle vs Shocks",
        labels={"abs_amount": "€ Amount", "cost_type_str": "Cost Type"},
        color_discrete_map=COLORS,
        category_orders={"cost_type_str": ["unclassified", "special", "variable", "fixed"]},
        template=PLOTLY_TEMPLATE
    )
    
    # Add Income Line if possible
    inc_trend = income_df.copy()
    if not inc_trend.empty:
        inc_trend["month"] = inc_trend["booking_date"].dt.to_period("M").astype(str)
        inc_m = inc_trend.groupby("month")["amount"].sum().reset_index()
        fig_steering.add_scatter(x=inc_m["month"], y=inc_m["amount"], name="Net Income", line=dict(color="#ffffff", width=2))

    st.plotly_chart(fig_steering, use_container_width=True, key="control_steering_bar")

    st.markdown("---")

    # 2. THE EFFICIENCY MATRIX: 3-Column Top Payees
    st.subheader("The Efficiency Matrix: Top Receivers")
    
    # Month Selection for the Matrix
    matrix_months = sorted(expense_df["booking_date"].dt.to_period("M").unique().astype(str).tolist(), reverse=True)
    sel_month = st.selectbox("Select Month for Matrix Analysis", ["Full Period"] + matrix_months, key="matrix_month_sel")
    
    # Filter matrix data
    matrix_df = expense_df.copy()
    if sel_month != "Full Period":
        matrix_df["month_str"] = matrix_df["booking_date"].dt.to_period("M").astype(str)
        matrix_df = matrix_df[matrix_df["month_str"] == sel_month]

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🛡️ Fixed (Structural)**")
        f_df = matrix_df[matrix_df["cost_type_str"] == "fixed"]
        if not f_df.empty:
            top_f = f_df.groupby("raw_payee")["abs_amount"].sum().nlargest(10).reset_index()
            st.dataframe(top_f, use_container_width=True, hide_index=True)
        else:
            st.caption("No fixed costs.")

    with col2:
        st.markdown("**🏃 Variable (Lifestyle)**")
        v_df = matrix_df[matrix_df["cost_type_str"] == "variable"]
        if not v_df.empty:
            top_v = v_df.groupby("raw_payee")["abs_amount"].sum().nlargest(10).reset_index()
            st.dataframe(top_v, use_container_width=True, hide_index=True)
        else:
            st.caption("No variable costs.")

    with col3:
        st.markdown("**⚡ Special (Shocks)**")
        s_df = matrix_df[matrix_df["cost_type_str"] == "special"]
        if not s_df.empty:
            top_s = s_df.groupby("raw_payee")["abs_amount"].sum().nlargest(10).reset_index()
            st.dataframe(top_s, use_container_width=True, hide_index=True)
        else:
            st.caption("No special costs.")

    st.markdown("---")

    # 3. ASSET WATCH: House & Vehicle
    st.subheader("High-Value Asset Tracking")
    a1, a2 = st.columns(2)
    
    house_total = expense_df[expense_df["is_house_related"] == True]["abs_amount"].sum()
    vehicle_total = expense_df[expense_df["main_category"].str.contains("Auto|Mobilität", na=False)]["abs_amount"].sum()
    
    with a1:
        st.metric("Total House Costs", f"€{house_total:,.0f}", help="Sum of all house-related transactions")
    with a2:
        st.metric("Total Vehicle Costs", f"€{vehicle_total:,.0f}", help="Sum of Mobility / Auto categories")

    st.markdown("---")

    # 4. DRILL-DOWN: Category Explorer
    st.subheader("Interactive Category Explorer")
    main_cat = st.selectbox("Select Main Category", ["All"] + list(expense_df["main_category"].unique()))
    
    view_df = expense_df.copy()
    if main_cat != "All":
        view_df = view_df[view_df["main_category"] == main_cat]
        
    sub_breakdown = view_df.groupby("sub_category")["abs_amount"].agg(["sum", "count"]).sort_values("sum", ascending=False).reset_index()
    sub_breakdown.columns = ["Sub-Category", "Total €", "Count"]
    st.dataframe(sub_breakdown, use_container_width=True, hide_index=True)
