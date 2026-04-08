import streamlit as st
import pandas as pd

def render_sidebar(df_raw, accounts_df):
    """
    Renders the sidebar filters and data health metrics.
    Returns a dictionary with filter results.
    """
    st.sidebar.markdown("## 🏦 Finance Cockpit")
    st.sidebar.markdown("---")

    # Account Filter
    if not accounts_df.empty:
        all_names = accounts_df["bank_name"].unique().tolist()
        sel_accounts = st.sidebar.multiselect("Accounts", all_names, default=all_names)
        valid_ids = accounts_df[accounts_df["bank_name"].isin(sel_accounts)]["id"].tolist()
        df_f = df_raw[df_raw["account_id"].isin(valid_ids)].copy()
    else:
        df_f = df_raw.copy()

    # Timeframe Filter
    tf = st.sidebar.radio("Timeframe", ["This Month", "Last 3 Months", "YTD", "All Time"], index=3, horizontal=True)
    mx = df_f["booking_date"].max() if not df_f.empty else pd.Timestamp.now()

    if tf == "This Month":
        sd = mx.replace(day=1)
    elif tf == "Last 3 Months":
        sd = (mx - pd.DateOffset(months=3)).replace(day=1)
    elif tf == "YTD":
        sd = mx.replace(month=1, day=1)
    else:
        sd = df_f["booking_date"].min() if not df_f.empty else pd.Timestamp.now()

    df_filtered = df_f[df_f["booking_date"] >= sd]

    # Data Health Metrics
    total_tx = len(df_filtered)
    needs_rev = int(df_filtered["needs_review"].sum()) if not df_filtered.empty else 0
    categorized = total_tx - needs_rev
    pct = (categorized / total_tx * 100) if total_tx > 0 else 0

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Data Health")
    st.sidebar.metric("Total Transactions", f"{total_tx:,}")
    st.sidebar.metric("Categorized", f"{categorized:,} ({pct:.0f}%)")
    
    if needs_rev > 0:
        st.sidebar.warning(f"⚠ {needs_rev} need review")
    else:
        st.sidebar.success("✅ Inbox Zero")

    date_min = df_filtered["booking_date"].min().strftime("%Y-%m") if not df_filtered.empty else "—"
    date_max = df_filtered["booking_date"].max().strftime("%Y-%m") if not df_filtered.empty else "—"
    st.sidebar.caption(f"Data range: {date_min} → {date_max}")

    return {
        "df_filtered": df_filtered,
        "start_date": sd,
        "max_date": mx,
        "needs_review_count": needs_rev
    }
