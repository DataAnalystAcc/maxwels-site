import streamlit as st
import os
import sys

# Dashboard file structure:
# dashboard/
# ├── app.py                      # Main entry & Routing
# ├── config.py                   # UI Tokens & Constants
# ├── services/                  
# │   ├── data_loader.py          # Session & Caching
# │   └── queries.py               # Pure Pandas Business Logic
# ├── components/                 
# │   ├── sidebar.py              # Filter controls
# │   ├── kpis.py                 # Metric Cards
# │   └── charts.py               # Plotly Visuals
# └── pages/                      
#     ├── overview.py             # Landing KPIs
#     ├── cashflow.py             # Income/Expense Delta
#     ├── spending.py             # Category Tree & Merchants
#     ├── recurring.py            # Fixed Costs & Subs
#     ├── special_views.py        # House/Car/Travel Deep Dives
#     ├── inbox.py                # Review Queue
#     └── rules.py                # Rules Database

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.services.data_loader import load_all, get_db
from dashboard.services.queries import split_core, get_prev_period_data
from dashboard.components.sidebar import render_sidebar
from dashboard.pages import overview, cashflow, spending, recurring, special_views, inbox, rules, cost_control

st.set_page_config(page_title="Personal Finance Cockpit", layout="wide", page_icon="🏦")

db = get_db()
df_raw, accounts_df = load_all(db)

# 1. Global Filter Context
ctx = render_sidebar(df_raw, accounts_df)

# 2. Financial Metrics Service Call
df_core, income_df, expense_df = split_core(ctx["df_filtered"])
prev_data = get_prev_period_data(df_raw, ctx["start_date"], ctx["max_date"])

# 3. Information Architecture (Routing)
inbox_btn = f"📬 Inbox ({ctx['needs_review_count']})" if ctx["needs_review_count"] > 0 else "📬 Inbox"

tab_list = ["📊 Overview", "⏳ Cashflow", "💳 Spending", "🕹️ Control", "🔒 Recurring", "🏠 Special Views", inbox_btn, "⚙️ Rules"]
t1, t2, t3, tc, t4, t5, t6, t7 = st.tabs(tab_list)

with t1: overview.render(df_core, income_df, expense_df, prev_data, ctx, df_raw)
with t2: cashflow.render(df_core)
with t3: spending.render(expense_df)
with tc: cost_control.render(df_core, income_df, expense_df)
with t4: recurring.render(expense_df, db)
with t5: special_views.render(expense_df)
with t6: inbox.render(df_raw, db, load_all)
with t7: rules.render(db)

db.close()
