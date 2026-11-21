"""
plots.py - Interactive Plotly and Static Matplotlib Visualization Suite
========================================================================
Implements professional, publication-grade visual charts:
1. Category-wise spending bar chart.
2. Monthly spending trend line chart.
3. Payment-method distribution pie chart.
4. Daily spending trend line chart with rolling average.
5. Income versus Expenses grouped bar chart.
6. Budget versus Actual spending comparison bar chart.
7. Category spending distribution donut chart.
"""

from typing import Optional, Any
import pandas as pd
import numpy as np

# Plotly imports
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    px = None
    go = None

# Matplotlib imports
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Color theme palette
PALETTE = [
    "#2b5c8f", "#e6550d", "#31a354", "#756bb1", "#e7298a",
    "#6baed6", "#fd8d3c", "#74c476", "#9e9ac8", "#df65b0",
    "#bcbddc", "#fdae6b"
]


def _empty_figure(message: str = "No data available for the selected period.") -> Any:
    """Return an annotated blank Plotly figure when dataset is empty."""
    if go is None:
        return None
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="#6c757d")
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


# ============================================================================
# 1. Category-Wise Spending Bar Chart (Required Chart 1)
# ============================================================================

def plot_category_bar(category_df: pd.DataFrame) -> Any:
    """
    Vertical or horizontal bar chart displaying total spending per category.
    """
    if category_df is None or category_df.empty or go is None:
        return _empty_figure("No category spending data available.")

    df_sorted = category_df.sort_values(by="total_spending", ascending=True)

    fig = go.Figure(go.Bar(
        x=df_sorted["total_spending"],
        y=df_sorted["category"],
        orientation="h",
        marker=dict(
            color=df_sorted["total_spending"],
            colorscale="Teal",
            line=dict(color="#1f497d", width=1)
        ),
        text=[f"₹{val:,.2f}" for val in df_sorted["total_spending"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Total Spending: ₹%{x:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        title="<b>Category-Wise Total Spending</b>",
        title_font=dict(size=16, color="#1e293b"),
        xaxis_title="Spending (₹ INR)",
        yaxis_title="Category",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=420,
        margin=dict(l=40, r=60, t=50, b=40),
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0")
    )
    return fig


# ============================================================================
# 2. Monthly Spending Trend Line Chart (Required Chart 2)
# ============================================================================

def plot_monthly_trend_line(monthly_df: pd.DataFrame) -> Any:
    """
    Line chart tracking monthly expenses over time with markers and currency formatting.
    """
    if monthly_df is None or monthly_df.empty or go is None:
        return _empty_figure("No monthly expense data available.")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=monthly_df["month"],
        y=monthly_df["expenses"],
        mode="lines+markers+text",
        name="Monthly Expenses",
        line=dict(color="#e11d48", width=3),
        marker=dict(size=8, color="#9f1239"),
        text=[f"₹{v:,.0f}" for v in monthly_df["expenses"]],
        textposition="top center",
        hovertemplate="<b>Month: %{x}</b><br>Expense: ₹%{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        title="<b>Monthly Spending Trend</b>",
        title_font=dict(size=16, color="#1e293b"),
        xaxis_title="Month",
        yaxis_title="Total Expenses (₹ INR)",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0")
    )
    return fig


# ============================================================================
# 3. Payment-Method Distribution Pie / Donut Chart (Required Chart 3)
# ============================================================================

def plot_payment_method_pie(account_df: pd.DataFrame) -> Any:
    """
    Donut / Pie chart illustrating expenditure distribution across payment methods.
    """
    if account_df is None or account_df.empty or go is None:
        return _empty_figure("No payment method spending data available.")

    fig = go.Figure(go.Pie(
        labels=account_df["account"],
        values=account_df["total_spending"],
        hole=0.45,
        marker=dict(colors=PALETTE),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Spending: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>"
    ))

    fig.update_layout(
        title="<b>Payment Method Distribution</b>",
        title_font=dict(size=16, color="#1e293b"),
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    return fig


# ============================================================================
# 4. Daily Spending Trend Chart (Required Chart 4)
# ============================================================================

def plot_daily_trend(daily_df: pd.DataFrame) -> Any:
    """
    Daily spending line chart with an overlaid 7-day rolling average trendline.
    """
    if daily_df is None or daily_df.empty or go is None:
        return _empty_figure("No daily spending data available.")

    fig = go.Figure()

    # Daily expenses bar
    fig.add_trace(go.Bar(
        x=daily_df["tx_date"],
        y=daily_df["daily_expense"],
        name="Daily Outflow",
        marker=dict(color="#cbd5e1"),
        hovertemplate="<b>Date: %{x}</b><br>Daily Spend: ₹%{y:,.2f}<extra></extra>"
    ))

    # 7-day moving average line
    if "rolling_avg_7d" in daily_df.columns:
        fig.add_trace(go.Scatter(
            x=daily_df["tx_date"],
            y=daily_df["rolling_avg_7d"],
            mode="lines",
            name="7-Day Rolling Avg",
            line=dict(color="#2563eb", width=2.5),
            hovertemplate="<b>Date: %{x}</b><br>7D Rolling Avg: ₹%{y:,.2f}<extra></extra>"
        ))

    fig.update_layout(
        title="<b>Daily Spending Trajectory & 7-Day Moving Average</b>",
        title_font=dict(size=16, color="#1e293b"),
        xaxis_title="Date",
        yaxis_title="Spending (₹ INR)",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


# ============================================================================
# Additional Chart: Income vs. Expenses Grouped Bar Chart
# ============================================================================

def plot_income_vs_expense(monthly_df: pd.DataFrame) -> Any:
    """
    Grouped bar chart comparing Monthly Inflow (Income) vs Outflow (Expenses).
    """
    if monthly_df is None or monthly_df.empty or go is None:
        return _empty_figure("No monthly data available for comparison.")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=monthly_df["month"],
        y=monthly_df["income"],
        name="Income",
        marker=dict(color="#10b981"),
        text=[f"₹{v:,.0f}" for v in monthly_df["income"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Income: ₹%{y:,.2f}<extra></extra>"
    ))

    fig.add_trace(go.Bar(
        x=monthly_df["month"],
        y=monthly_df["expenses"],
        name="Expenses",
        marker=dict(color="#ef4444"),
        text=[f"₹{v:,.0f}" for v in monthly_df["expenses"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Expenses: ₹%{y:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        title="<b>Monthly Inflow (Income) vs Outflow (Expenses)</b>",
        title_font=dict(size=16, color="#1e293b"),
        barmode="group",
        xaxis_title="Month",
        yaxis_title="Amount (₹ INR)",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


# ============================================================================
# Additional Chart: Budget vs Actual Spending Comparison Bar Chart
# ============================================================================

def plot_budget_vs_actual(budget_status_df: pd.DataFrame) -> Any:
    """
    Horizontal grouped bar chart comparing Budget Limits vs Actual Spending per category.
    """
    if budget_status_df is None or budget_status_df.empty or go is None:
        return _empty_figure("No active monthly budgets defined to compare.")

    df_sorted = budget_status_df.sort_values(by="budget_limit", ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_sorted["category"],
        x=df_sorted["budget_limit"],
        name="Budget Limit",
        orientation="h",
        marker=dict(color="#94a3b8"),
        text=[f"₹{v:,.0f}" for v in df_sorted["budget_limit"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Limit: ₹%{x:,.2f}<extra></extra>"
    ))

    fig.add_trace(go.Bar(
        y=df_sorted["category"],
        x=df_sorted["actual_spending"],
        name="Actual Spent",
        orientation="h",
        marker=dict(color="#3b82f6"),
        text=[f"₹{v:,.0f}" for v in df_sorted["actual_spending"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Spent: ₹%{x:,.2f}<extra></extra>"
    ))

    fig.update_layout(
        title="<b>Budget Limit vs Actual Spending</b>",
        title_font=dict(size=16, color="#1e293b"),
        barmode="group",
        xaxis_title="Amount (₹ INR)",
        yaxis_title="Category",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        height=420,
        margin=dict(l=40, r=60, t=50, b=40),
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


# ============================================================================
# Additional Chart: Category Spending Distribution Donut Chart
# ============================================================================

def plot_category_donut(category_df: pd.DataFrame) -> Any:
    """
    Donut chart of category spending percentages.
    """
    if category_df is None or category_df.empty or go is None:
        return _empty_figure("No category spending data available.")

    fig = go.Figure(go.Pie(
        labels=category_df["category"],
        values=category_df["total_spending"],
        hole=0.45,
        marker=dict(colors=PALETTE),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Spending: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>"
    ))

    fig.update_layout(
        title="<b>Category Spending Share</b>",
        title_font=dict(size=16, color="#1e293b"),
        paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    return fig
