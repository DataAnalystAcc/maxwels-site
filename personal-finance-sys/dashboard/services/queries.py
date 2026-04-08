import pandas as pd
from datetime import timedelta

def mom_delta(current_val: float, prev_val: float):
    """Returns (delta_str, delta_val) suitable for st.metric."""
    if prev_val == 0:
        return None
    pct_change = ((current_val - prev_val) / abs(prev_val)) * 100
    return f"{pct_change:+.1f}%"


def split_core(df):
    """
    Splits dataframe into core (no transfers), income, and expense dataframes.
    Treats refunds (positive amounts in non-income categories) as negative expenses.
    """
    df_core = df[df["is_internal_transfer"] == False].copy()
    
    # Identify Income (Einnahmen)
    income_mask = (df_core["amount"] > 0) & (df_core["main_category"] == "Einnahmen")
    income_df = df_core[income_mask].copy()
    
    # Identify Expenses & Refunds
    expense_mask = ~income_mask
    expense_df = df_core[expense_mask].copy()
    
    # Standardize: Expenses are positive numbers, Refunds are negative numbers in this DF
    # If amount is > 0 but not in Income category, it's a refund (negative expense)
    expense_df["abs_amount"] = -expense_df["amount"] 
        
    return df_core, income_df, expense_df

def get_liquid_runway(df_raw):
    """Returns total current balance across all checking/cash accounts."""
    if df_raw.empty: return 0.0
    return df_raw.groupby("account_id")["amount"].sum().sum()

def get_steering_metrics(df_raw, start_date, max_date):
    """
    Returns MTD and Rolling 3M metrics for steering KPIs.
    """
    # 1. MTD Context
    mtd_start = max_date.replace(day=1)
    df_mtd = df_raw[df_raw["booking_date"] >= mtd_start]
    _, inc_mtd_alt, exp_mtd_alt = split_core(df_mtd)
    
    inc_mtd = inc_mtd_alt["amount"].sum()
    fixed_mtd = exp_mtd_alt[exp_mtd_alt["cost_type_str"] == "fixed"]["abs_amount"].sum()
    var_mtd = exp_mtd_alt[
        (exp_mtd_alt["cost_type_str"] == "variable") & (exp_mtd_alt["is_travel_related"] == False)
    ]["abs_amount"].sum()
    
    # 2. Previous Month Equivalent (Day 1 to Day N)
    days_passed = (max_date - mtd_start).days
    prev_month_start = (mtd_start - pd.DateOffset(months=1))
    prev_month_end = prev_month_start + pd.DateOffset(days=days_passed)
    
    df_prev = df_raw[(df_raw["booking_date"] >= prev_month_start) & (df_raw["booking_date"] <= prev_month_end)]
    _, inc_p, exp_p = split_core(df_prev)
    
    inc_p_sum = inc_p["amount"].sum()
    fixed_p_sum = exp_p[exp_p["cost_type_str"] == "fixed"]["abs_amount"].sum()
    var_p_sum = exp_p[(exp_p["cost_type_str"] == "variable") & (exp_p["is_travel_related"] == False)]["abs_amount"].sum()

    # 3. Rolling 3M Context for Savings Rate
    r3m_start = (max_date - pd.DateOffset(months=3)).replace(day=1)
    df_r3m = df_raw[df_raw["booking_date"] >= r3m_start]
    _, inc_r, exp_r = split_core(df_r3m)
    
    inc_r_sum = inc_r["amount"].sum()
    exp_r_sum = exp_r["abs_amount"].sum()
    sr_r3m = ((inc_r_sum - exp_r_sum) / inc_r_sum * 100) if inc_r_sum > 0 else 0
    
    # 4. Data Health (Categorization Rate)
    # Exclude internal transfers from health check
    health_df = df_raw[df_raw["is_internal_transfer"] == False]
    total_non_transfer = len(health_df)
    if total_non_transfer > 0:
        unclassified_count = len(health_df[health_df["cost_type_str"] == "unclassified"])
        data_health = (1 - (unclassified_count / total_non_transfer)) * 100
    else:
        data_health = 100.0

    return {
        "inc_mtd": inc_mtd, "inc_p": inc_p_sum,
        "fixed_mtd": fixed_mtd, "fixed_p": fixed_p_sum,
        "var_mtd": var_mtd, "var_p": var_p_sum,
        "sr_r3m": sr_r3m,
        "data_health": data_health,
        "liquid_runway": get_liquid_runway(df_raw)
    }

def get_prev_period_data(df_raw, start_date, max_date):
    """
    Get the equivalent prior period metrics based on current filter.
    """
    if df_raw.empty:
        return 0.0, 0.0, 0.0
        
    period_len = (max_date - start_date).days
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_len)
    
    prev = df_raw[
        (df_raw["booking_date"] >= prev_start)
        & (df_raw["booking_date"] <= prev_end)
        & (df_raw["is_internal_transfer"] == False)
    ]
    
    prev_inc = prev[prev["amount"] > 0]["amount"].sum()
    prev_exp = prev[prev["amount"] < 0].copy()
    
    if not prev_exp.empty:
        prev_exp["abs_amount"] = prev_exp["amount"].abs()
        # Note: we use 'cost_type_str' which is added in data_loader
        prev_fixed = prev_exp[prev_exp["cost_type_str"] == "fixed"]["abs_amount"].sum()
        prev_var = prev_exp[
            (prev_exp["cost_type_str"] == "variable") & (prev_exp["is_travel_related"] == False)
        ]["abs_amount"].sum()
    else:
        prev_fixed = 0.0
        prev_var = 0.0
        
    return prev_inc, prev_fixed, prev_var
