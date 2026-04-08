import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from dashboard.config import COLORS, PLOTLY_TEMPLATE

def cashflow_bar(df_core):
    """Monthly Income vs Expenses bar chart."""
    cf = df_core.copy()
    cf["month"] = cf["booking_date"].dt.to_period("M").astype(str)
    cf["type"] = np.where(cf["amount"] > 0, "Income", "Expenses")
    mcf = cf.groupby(["month", "type"])["amount"].sum().reset_index()
    mcf["amount"] = mcf["amount"].abs()
    
    fig = px.bar(
        mcf, x="month", y="amount", color="type", barmode="group",
        color_discrete_map={"Income": COLORS["income"], "Expenses": COLORS["expense"]},
        template=PLOTLY_TEMPLATE
    )
    fig.update_layout(xaxis_title="", yaxis_title="€", legend_title="", margin=dict(t=10, b=30))
    return fig

def running_balance(df_filtered):
    """Cumulative balance line chart."""
    bal = df_filtered.sort_values("booking_date").copy()
    bal["cumulative"] = bal["amount"].cumsum()
    
    fig = px.line(bal, x="booking_date", y="cumulative", template=PLOTLY_TEMPLATE, line_shape="hv")
    fig.update_traces(line_color=COLORS["income"], fill="tozeroy", fillcolor="rgba(0,200,83,0.08)")
    fig.update_layout(xaxis_title="", yaxis_title="€ Balance", margin=dict(t=10, b=30))
    return fig

def cost_type_breakdown(expense_df):
    """Stacked bar chart of cost types over time."""
    et = expense_df.copy()
    et["month"] = et["booking_date"].dt.to_period("M").astype(str)
    ct_month = et.groupby(["month", "cost_type_str"])["abs_amount"].sum().reset_index()
    
    fig = px.bar(
        ct_month, x="month", y="abs_amount", color="cost_type_str", barmode="stack",
        color_discrete_map=COLORS, template=PLOTLY_TEMPLATE
    )
    fig.update_layout(xaxis_title="", yaxis_title="€ Spend", legend_title="Cost Type", margin=dict(t=10, b=30))
    return fig

def category_treemap(expense_df):
    """Hierarchical treemap of spending."""
    cat_s = expense_df.groupby(["main_category", "sub_category"])["abs_amount"].sum().reset_index()
    cat_s.fillna("Uncategorized", inplace=True)
    cat_s = cat_s[cat_s["abs_amount"] > 0]
    
    fig = px.treemap(
        cat_s, path=[px.Constant("All Expenses"), "main_category", "sub_category"],
        values="abs_amount", template=PLOTLY_TEMPLATE
    )
    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10))
    return fig

def merchant_bar(expense_df):
    """Horizontal bar chart of top 10 merchants."""
    top_m = expense_df.groupby("raw_payee")["abs_amount"].sum().nlargest(10).reset_index()
    fig = px.bar(
        top_m, x="abs_amount", y="raw_payee", orientation="h", template=PLOTLY_TEMPLATE,
        color_discrete_sequence=[COLORS["variable"]]
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="€", yaxis_title="", margin=dict(t=10))
    return fig

def category_trends(expense_df):
    """Line chart of main categories over time."""
    et2 = expense_df.copy()
    et2["month"] = et2["booking_date"].dt.to_period("M").astype(str)
    cat_trend = et2.groupby(["month", "main_category"])["abs_amount"].sum().reset_index()
    
    fig = px.line(
        cat_trend, x="month", y="abs_amount", color="main_category",
        template=PLOTLY_TEMPLATE, markers=True
    )
    fig.update_layout(xaxis_title="", yaxis_title="€", legend_title="", margin=dict(t=10))
    return fig
