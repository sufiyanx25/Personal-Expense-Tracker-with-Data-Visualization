"""
analyze.py - Financial Data Analytics and Metric Computation
=============================================================
Calculates core financial KPIs, monthly aggregations, category breakdowns,
payment method shares, savings rate, and spending trends with robust handling
for empty datasets and zero income.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def get_financial_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute core financial summary KPIs:
    - total_income: Sum of positive transactions.
    - total_expenses: Absolute sum of negative transactions.
    - total_savings: Total Income - Total Expenses.
    - savings_rate: (Savings / Total Income) * 100 if Income > 0 else 0.0.
    - highest_spending_category: Category with maximum outflow.
    - avg_daily_spending: Average expense per distinct active transaction day.
    """
    if df is None or df.empty:
        return {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "total_savings": 0.0,
            "savings_rate": 0.0,
            "highest_spending_category": "N/A",
            "highest_spending_amount": 0.0,
            "avg_daily_spending": 0.0,
            "transaction_count": 0
        }

    # Strict isolation: Income (>0) vs Expenses (<0)
    income_mask = df["amount"] > 0
    expense_mask = df["amount"] < 0

    total_income = float(df.loc[income_mask, "amount"].sum())
    total_expenses = float(abs(df.loc[expense_mask, "amount"].sum()))
    total_savings = float(total_income - total_expenses)

    if total_income > 0:
        savings_rate = float((total_savings / total_income) * 100.0)
    else:
        savings_rate = 0.0

    # Highest spending category
    exp_df = df[expense_mask].copy()
    if not exp_df.empty and "category" in exp_df.columns:
        cat_sums = exp_df.groupby("category")["amount"].sum().abs()
        highest_cat = str(cat_sums.idxmax())
        highest_amt = float(cat_sums.max())
    else:
        highest_cat = "N/A"
        highest_amt = 0.0

    # Average daily spending
    if not exp_df.empty and "tx_date" in exp_df.columns:
        active_days = exp_df["tx_date"].nunique()
        avg_daily = float(total_expenses / max(active_days, 1))
    else:
        avg_daily = 0.0

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "total_savings": round(total_savings, 2),
        "savings_rate": round(savings_rate, 2),
        "highest_spending_category": highest_cat,
        "highest_spending_amount": round(highest_amt, 2),
        "avg_daily_spending": round(avg_daily, 2),
        "transaction_count": int(len(df))
    }


def get_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate income, expenses, savings, and savings rate by month (YYYY-MM).
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["month", "income", "expenses", "savings", "savings_rate"])

    temp = df.copy()
    temp["month"] = temp["tx_date"].astype(str).str.slice(0, 7)

    months = sorted(temp["month"].unique())
    records = []

    for m in months:
        m_df = temp[temp["month"] == m]
        kpis = get_financial_kpis(m_df)
        records.append({
            "month": m,
            "income": kpis["total_income"],
            "expenses": kpis["total_expenses"],
            "savings": kpis["total_savings"],
            "savings_rate": kpis["savings_rate"]
        })

    return pd.DataFrame(records)


def get_category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate expenditure grouped by category (expenses only):
    - Category
    - Total Spending
    - Transaction Count
    - Percentage of Total Spending
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["category", "total_spending", "count", "percentage"])

    exp_df = df[df["amount"] < 0].copy()
    if exp_df.empty:
        return pd.DataFrame(columns=["category", "total_spending", "count", "percentage"])

    exp_df["spending"] = exp_df["amount"].abs()
    grouped = exp_df.groupby("category").agg(
        total_spending=("spending", "sum"),
        count=("spending", "count")
    ).reset_index()

    total_all_expenses = grouped["total_spending"].sum()
    if total_all_expenses > 0:
        grouped["percentage"] = (grouped["total_spending"] / total_all_expenses) * 100.0
    else:
        grouped["percentage"] = 0.0

    grouped = grouped.sort_values(by="total_spending", ascending=False).reset_index(drop=True)
    grouped["total_spending"] = grouped["total_spending"].round(2)
    grouped["percentage"] = grouped["percentage"].round(2)
    return grouped


def get_payment_method_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate spending breakdown grouped by payment account/method.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["account", "total_spending", "count", "percentage"])

    exp_df = df[df["amount"] < 0].copy()
    if exp_df.empty:
        return pd.DataFrame(columns=["account", "total_spending", "count", "percentage"])

    exp_df["spending"] = exp_df["amount"].abs()
    grouped = exp_df.groupby("account").agg(
        total_spending=("spending", "sum"),
        count=("spending", "count")
    ).reset_index()

    total_spent = grouped["total_spending"].sum()
    if total_spent > 0:
        grouped["percentage"] = (grouped["total_spending"] / total_spent) * 100.0
    else:
        grouped["percentage"] = 0.0

    grouped = grouped.sort_values(by="total_spending", ascending=False).reset_index(drop=True)
    grouped["total_spending"] = grouped["total_spending"].round(2)
    grouped["percentage"] = grouped["percentage"].round(2)
    return grouped


def get_daily_spending_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate total expenditure per day and a 7-day rolling average.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["tx_date", "daily_expense", "rolling_avg_7d"])

    exp_df = df[df["amount"] < 0].copy()
    if exp_df.empty:
        return pd.DataFrame(columns=["tx_date", "daily_expense", "rolling_avg_7d"])

    exp_df["spending"] = exp_df["amount"].abs()
    daily = exp_df.groupby("tx_date")["spending"].sum().reset_index()
    daily = daily.rename(columns={"spending": "daily_expense"}).sort_values("tx_date")

    # 7-day rolling average
    daily["rolling_avg_7d"] = daily["daily_expense"].rolling(window=7, min_periods=1).mean().round(2)
    daily["daily_expense"] = daily["daily_expense"].round(2)
    return daily
