import streamlit as st
import plotly.express as px
from dashboard.config import PLOTLY_TEMPLATE, COLORS

def render(expense_df):
    """
    Renders the Assets deep-dive tab content (House, Car, Travel, Debt).
    """
    asset_mode = st.pills(
        "View", ["🏠 House", "🚗 Car", "✈️ Travel", "💳 Debt"], 
        default="🏠 House"
    )
    st.markdown("---")

    if asset_mode == "🏠 House":
        h_df = expense_df[expense_df["is_house_related"] == True]
        if h_df.empty:
            st.info("No house-related transactions found.")
        else:
            st.metric("Total Property Costs", f"€{h_df['abs_amount'].sum():,.0f}")
            cl, cr = st.columns(2)
            with cl:
                ht = h_df.copy()
                ht["month"] = ht["booking_date"].dt.to_period("M").astype(str)
                hm = ht.groupby(["month", "sub_category"])["abs_amount"].sum().reset_index()
                fig_h = px.bar(hm, x="month", y="abs_amount", color="sub_category", template=PLOTLY_TEMPLATE)
                fig_h.update_layout(xaxis_title="", yaxis_title="€", margin=dict(t=10))
                st.plotly_chart(fig_h, use_container_width=True)
            with cr:
                top_h = h_df.groupby("raw_payee")["abs_amount"].sum().nlargest(8).reset_index()
                fig_th = px.bar(
                    top_h, x="abs_amount", y="raw_payee", orientation="h", 
                    template=PLOTLY_TEMPLATE, color_discrete_sequence=["#42a5f5"]
                )
                fig_th.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="€", yaxis_title="", margin=dict(t=10))
                st.plotly_chart(fig_th, use_container_width=True)

    elif asset_mode == "🚗 Car":
        car_df = expense_df[expense_df["main_category"] == "Mobilität / Auto"]
        if car_df.empty:
            st.info("No car-related transactions found.")
        else:
            fuel = car_df[car_df["sub_category"] == "Tanken"]["abs_amount"].sum()
            other = car_df[car_df["sub_category"] != "Tanken"]["abs_amount"].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Auto", f"€{car_df['abs_amount'].sum():,.0f}")
            m2.metric("Fuel", f"€{fuel:,.0f}")
            m3.metric("Insurance / Tax / Other", f"€{other:,.0f}")
            st.dataframe(
                car_df[["booking_date", "raw_payee", "sub_category", "amount"]].sort_values("booking_date", ascending=False),
                use_container_width=True, hide_index=True,
            )

    elif asset_mode == "✈️ Travel":
        tr_df = expense_df[expense_df["is_travel_related"] == True]
        if tr_df.empty:
            st.info("No travel-related transactions found.")
        else:
            st.metric("Total Travel", f"€{tr_df['abs_amount'].sum():,.0f}")
            fig_tr = px.pie(tr_df, names="sub_category", values="abs_amount", hole=0.4, template=PLOTLY_TEMPLATE)
            fig_tr.update_layout(margin=dict(t=10))
            st.plotly_chart(fig_tr, use_container_width=True)
            with st.expander("Transaction Detail"):
                st.dataframe(
                    tr_df[["booking_date", "raw_payee", "sub_category", "amount"]].sort_values("booking_date", ascending=False),
                    use_container_width=True, hide_index=True,
                )

    elif asset_mode == "💳 Debt":
        debt_df = expense_df[expense_df["main_category"] == "Schulden / Kredit / Rückzahlung"]
        if debt_df.empty:
            st.info("No debt repayment transactions found.")
        else:
            st.metric("Total Repaid", f"€{debt_df['abs_amount'].sum():,.0f}")
            dt = debt_df.copy()
            dt["month"] = dt["booking_date"].dt.to_period("M").astype(str)
            dm = dt.groupby("month")["abs_amount"].sum().cumsum().reset_index()
            dm.columns = ["month", "cumulative"]
            fig_d = px.area(
                dm, x="month", y="cumulative", template=PLOTLY_TEMPLATE,
                color_discrete_sequence=[COLORS["expense"]]
            )
            fig_d.update_layout(xaxis_title="", yaxis_title="€ Cumulative", margin=dict(t=10))
            st.plotly_chart(fig_d, use_container_width=True)
