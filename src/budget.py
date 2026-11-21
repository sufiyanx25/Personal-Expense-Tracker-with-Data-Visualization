"""
budget.py - Budget Management, Tracking, and Threshold Alerting Engine
======================================================================
Provides CRUD operations for monthly category budgets, calculates actual
spending vs budget limits, variance, remaining balances, and alert status flags:
'Within Budget', 'Approaching Budget' (>=80%), and 'Budget Exceeded' (>100%).
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from .models import get_connection, DEFAULT_DB_PATH


def set_budget(
    month: str,
    category_name: str,
    limit_amount: float,
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[bool, str]:
    """
    Create or update a budget limit for a category in a specific month (YYYY-MM).
    """
    month_clean = str(month).strip()
    cat_clean = str(category_name).strip()

    if not month_clean or len(month_clean) != 7 or "-" not in month_clean:
        return False, "Invalid month format. Please use 'YYYY-MM' (e.g., '2024-10')."

    if not cat_clean:
        return False, "Category name cannot be empty."

    try:
        limit_val = float(limit_amount)
        if limit_val <= 0:
            return False, "Budget limit must be a positive number greater than 0."
    except (ValueError, TypeError):
        return False, "Invalid numeric limit amount."

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO budgets (month, category_name, limit_amount)
            VALUES (?, ?, ?)
            ON CONFLICT(month, category_name) DO UPDATE SET limit_amount = excluded.limit_amount
            """,
            (month_clean, cat_clean, round(limit_val, 2))
        )
        conn.commit()
        return True, f"Budget for '{cat_clean}' in {month_clean} set to ₹{limit_val:,.2f}."
    except Exception as e:
        return False, f"Failed to save budget: {str(e)}"
    finally:
        conn.close()


def get_all_budgets(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Fetch all defined budgets sorted by month descending and category ascending.
    """
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT id, month, category_name, limit_amount FROM budgets ORDER BY month DESC, category_name ASC",
            conn
        )
        return df
    finally:
        conn.close()


def delete_budget(budget_id: int, db_path: str = DEFAULT_DB_PATH) -> Tuple[bool, str]:
    """
    Delete a budget record by its primary key ID.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM budgets WHERE id = ?", (int(budget_id),))
        conn.commit()
        if cursor.rowcount > 0:
            return True, "Budget successfully removed."
        return False, "Budget record not found."
    except Exception as e:
        return False, f"Error deleting budget: {str(e)}"
    finally:
        conn.close()


def get_budget_status(
    month: str,
    transactions_df: Optional[pd.DataFrame] = None,
    db_path: str = DEFAULT_DB_PATH
) -> pd.DataFrame:
    """
    Compare actual spending against allocated budgets for a specific month (YYYY-MM).
    Returns DataFrame with:
    - category
    - budget_limit
    - actual_spending
    - remaining_budget
    - utilization_percent
    - status ('Within Budget', 'Approaching Budget', 'Budget Exceeded')
    """
    month_clean = str(month).strip()
    conn = get_connection(db_path)
    try:
        budgets_df = pd.read_sql_query(
            "SELECT id, category_name, limit_amount FROM budgets WHERE month = ?",
            conn,
            params=(month_clean,)
        )
    finally:
        conn.close()

    if budgets_df.empty:
        return pd.DataFrame(columns=[
            "id", "category", "budget_limit", "actual_spending",
            "remaining_budget", "utilization_percent", "status"
        ])

    # If transactions_df not provided, fetch from database for this month
    if transactions_df is None:
        conn = get_connection(db_path)
        try:
            tx_query = """
            SELECT
                COALESCE(c.name, 'Uncategorized') AS category,
                ABS(t.amount) AS spending
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.amount < 0 AND t.tx_date LIKE ?
            """
            tx_data = pd.read_sql_query(tx_query, conn, params=(f"{month_clean}%",))
        finally:
            conn.close()
    else:
        # Filter provided transactions to target month & expenses
        tx_filtered = transactions_df[
            (transactions_df["amount"] < 0) &
            (transactions_df["tx_date"].astype(str).str.startswith(month_clean))
        ].copy()
        tx_data = pd.DataFrame({
            "category": tx_filtered["category"],
            "spending": tx_filtered["amount"].abs()
        })

    actual_by_cat = (
        tx_data.groupby("category")["spending"].sum().to_dict()
        if not tx_data.empty else {}
    )

    rows = []
    for _, b_row in budgets_df.iterrows():
        cat = b_row["category_name"]
        limit = float(b_row["limit_amount"])
        actual = float(actual_by_cat.get(cat, 0.0))
        remaining = limit - actual
        utilization = (actual / limit * 100.0) if limit > 0 else 0.0

        if actual > limit:
            status = "Budget Exceeded"
        elif utilization >= 80.0:
            status = "Approaching Budget"
        else:
            status = "Within Budget"

        rows.append({
            "id": int(b_row["id"]),
            "category": cat,
            "budget_limit": round(limit, 2),
            "actual_spending": round(actual, 2),
            "remaining_budget": round(remaining, 2),
            "utilization_percent": round(utilization, 2),
            "status": status
        })

    result_df = pd.DataFrame(rows)
    if not result_df.empty:
        result_df = result_df.sort_values(by="utilization_percent", ascending=False).reset_index(drop=True)
    return result_df


def get_overspending_alerts(budget_status_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Extract warning and exceeded alert notices from the budget comparison DataFrame.
    """
    if budget_status_df is None or budget_status_df.empty:
        return []

    alerts = []
    for _, row in budget_status_df.iterrows():
        if row["status"] == "Budget Exceeded":
            alerts.append({
                "type": "error",
                "category": row["category"],
                "message": (
                    f"Overspending Alert: '{row['category']}' has exceeded its budget by "
                    f"₹{abs(row['remaining_budget']):,.2f} "
                    f"(Spent: ₹{row['actual_spending']:,.2f} / Limit: ₹{row['budget_limit']:,.2f})."
                )
            })
        elif row["status"] == "Approaching Budget":
            alerts.append({
                "type": "warning",
                "category": row["category"],
                "message": (
                    f"Budget Warning: '{row['category']}' has utilized {row['utilization_percent']:.1f}% "
                    f"of its limit (Remaining: ₹{row['remaining_budget']:,.2f})."
                )
            })
    return alerts
