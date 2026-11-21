"""
ingest.py - Expense Data Ingestion, Validation, and Transaction Management
===========================================================================
Handles CSV importing with flexible column mapping, schema validation, duplicate detection,
manual transaction recording (with sign enforcement), editing, and deletion.
"""

from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
from .models import (
    get_connection,
    get_category_id_by_name,
    is_duplicate_transaction,
    DEFAULT_DB_PATH
)
from .categorize import rule_based_categorize

# Standard column aliases for flexible CSV mapping
COLUMN_ALIASES: Dict[str, List[str]] = {
    "tx_date": ["tx_date", "date", "transaction_date", "txn_date", "trans_date", "value_date"],
    "description": ["description", "desc", "narration", "particulars", "remarks", "details", "merchant"],
    "amount": ["amount", "amt", "transaction_amount", "txn_amount", "value"],
    "account": ["account", "account_type", "payment_mode", "mode", "payment_method", "channel"],
    "raw_source": ["raw_source", "source", "statement", "source_file"],
    "category": ["category", "cat", "category_name", "expense_category"],
    "tags": ["tags", "tag", "notes", "memo"]
}


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map uploaded CSV columns to internal standard schema using case-insensitive alias matching.
    """
    df = df.copy()
    lower_cols = {str(col).strip().lower(): col for col in df.columns}
    mapping = {}

    for standard_col, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in lower_cols:
                mapping[lower_cols[alias.lower()]] = standard_col
                break

    df = df.rename(columns=mapping)
    return df


def validate_date(date_val: Any) -> Optional[str]:
    """
    Attempt parsing diverse date formats and standardize to 'YYYY-MM-DD'.
    Returns None if parsing fails.
    """
    if pd.isna(date_val) or date_val is None:
        return None
    val_str = str(date_val).strip()
    if not val_str:
        return None

    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S",
        "%d-%b-%Y", "%d-%B-%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback to pandas to_datetime
    try:
        dt = pd.to_datetime(val_str, dayfirst=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def clean_amount(amount_val: Any) -> Optional[float]:
    """
    Sanitize and convert currency strings or numeric amounts to float.
    Handles '₹', commas, currency codes, and negative brackets.
    """
    if pd.isna(amount_val) or amount_val is None:
        return None
    if isinstance(amount_val, (int, float)):
        return float(amount_val)

    s = str(amount_val).strip()
    s = s.replace("₹", "").replace("Rs.", "").replace("INR", "").replace(",", "").strip()

    # Handle negative formatted like (1,200.00)
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1].strip()

    try:
        return float(s)
    except ValueError:
        return None


def validate_transactions(df: pd.DataFrame) -> Tuple[bool, List[str], pd.DataFrame]:
    """
    Validate DataFrame against required fields:
    - tx_date
    - description
    - amount
    Returns (is_valid, error_list, cleaned_df).
    """
    errors: List[str] = []
    df_std = standardize_columns(df)

    required = ["tx_date", "description", "amount"]
    missing_required = [col for col in required if col not in df_std.columns]
    if missing_required:
        errors.append(f"Missing mandatory CSV columns: {', '.join(missing_required)}")
        return False, errors, df_std

    cleaned_rows = []
    for idx, row in df_std.iterrows():
        row_num = idx + 1
        raw_date = row.get("tx_date")
        iso_date = validate_date(raw_date)
        if not iso_date:
            errors.append(f"Row {row_num}: Invalid date format '{raw_date}'")
            continue

        raw_amt = row.get("amount")
        amt_float = clean_amount(raw_amt)
        if amt_float is None:
            errors.append(f"Row {row_num}: Invalid numeric amount '{raw_amt}'")
            continue

        desc = str(row.get("description", "")).strip()
        if not desc:
            errors.append(f"Row {row_num}: Description cannot be empty")
            continue

        account = str(row.get("account", "UPI")).strip() or "UPI"
        raw_source = str(row.get("raw_source", "CSV_IMPORT")).strip() or "CSV_IMPORT"
        category = str(row.get("category", "")).strip()
        tags = str(row.get("tags", "")).strip()

        cleaned_rows.append({
            "tx_date": iso_date,
            "description": desc,
            "amount": amt_float,
            "account": account,
            "raw_source": raw_source,
            "category": category,
            "tags": tags
        })

    cleaned_df = pd.DataFrame(cleaned_rows)
    return len(cleaned_rows) > 0, errors, cleaned_df


def import_csv_to_db(
    file_or_path: Any,
    db_path: str = DEFAULT_DB_PATH
) -> Dict[str, Any]:
    """
    Ingest a CSV file or file buffer, validate records, detect duplicates,
    auto-categorize, and insert into the transactions table.
    """
    try:
        if hasattr(file_or_path, "read"):
            df = pd.read_csv(file_or_path)
        else:
            df = pd.read_csv(str(file_or_path))
    except Exception as e:
        return {
            "success": False,
            "imported": 0,
            "duplicates": 0,
            "errors": [f"Failed to read CSV: {str(e)}"]
        }

    is_valid, errors, cleaned_df = validate_transactions(df)
    if not is_valid or cleaned_df.empty:
        return {
            "success": False,
            "imported": 0,
            "duplicates": 0,
            "errors": errors if errors else ["No valid transaction records found in file."]
        }

    imported_count = 0
    duplicate_count = 0

    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        for _, row in cleaned_df.iterrows():
            tx_date = row["tx_date"]
            description = row["description"]
            amount = row["amount"]
            account = row["account"]
            raw_source = row["raw_source"]
            tags = row.get("tags", "")

            # Duplicate check
            if is_duplicate_transaction(tx_date, description, amount, account, db_path):
                duplicate_count += 1
                continue

            # Determine category
            cat_name = row.get("category")
            if not cat_name:
                cat_name = rule_based_categorize(description, amount)

            cat_id = get_category_id_by_name(cat_name, db_path)
            if cat_id is None:
                cat_id = get_category_id_by_name("Uncategorized", db_path)

            cursor.execute(
                """
                INSERT INTO transactions (tx_date, description, amount, currency, account, category_id, raw_source, tags)
                VALUES (?, ?, ?, 'INR', ?, ?, ?, ?)
                """,
                (tx_date, description, amount, account, cat_id, raw_source, tags)
            )
            imported_count += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "imported": imported_count,
        "duplicates": duplicate_count,
        "errors": errors[:10]  # Return top 10 warnings if any
    }


def add_manual_transaction(
    tx_date: str,
    description: str,
    amount: float,
    transaction_type: str,  # 'Expense' or 'Income'
    account: str,
    category_name: Optional[str] = None,
    tags: str = "",
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[bool, str, Optional[int]]:
    """
    Insert a manual transaction ensuring expense amounts are negative and income amounts are positive.
    """
    iso_date = validate_date(tx_date)
    if not iso_date:
        return False, f"Invalid date '{tx_date}'. Please use YYYY-MM-DD format.", None

    desc = str(description).strip()
    if not desc:
        return False, "Transaction description cannot be blank.", None

    try:
        val = float(amount)
        if val <= 0:
            return False, "Amount must be a positive number.", None
    except (ValueError, TypeError):
        return False, "Please provide a valid numeric amount.", None

    # Enforce sign convention: Expenses are negative, Income is positive
    stored_amount = -abs(val) if transaction_type.lower() == "expense" else abs(val)

    # Resolve category
    if not category_name or category_name.strip() == "" or category_name.lower() == "auto":
        category_name = rule_based_categorize(desc, stored_amount)

    cat_id = get_category_id_by_name(category_name, db_path)
    if cat_id is None:
        cat_id = get_category_id_by_name("Uncategorized", db_path)

    # Check duplicate
    acc = str(account).strip() or "Cash"
    if is_duplicate_transaction(iso_date, desc, stored_amount, acc, db_path):
        return False, "A matching transaction already exists for this date, description, amount, and account.", None

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (tx_date, description, amount, currency, account, category_id, raw_source, tags)
            VALUES (?, ?, ?, 'INR', ?, ?, 'MANUAL_ENTRY', ?)
            """,
            (iso_date, desc, stored_amount, acc, cat_id, str(tags).strip())
        )
        conn.commit()
        new_id = cursor.lastrowid
        return True, "Transaction successfully recorded.", new_id
    except Exception as e:
        return False, f"Database error: {str(e)}", None
    finally:
        conn.close()


def update_transaction(
    tx_id: int,
    tx_date: str,
    description: str,
    amount: float,
    account: str,
    category_name: str,
    tags: str = "",
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[bool, str]:
    """
    Update an existing transaction record by ID.
    """
    iso_date = validate_date(tx_date)
    if not iso_date:
        return False, "Invalid date format."

    desc = str(description).strip()
    if not desc:
        return False, "Description cannot be empty."

    cat_id = get_category_id_by_name(category_name, db_path)
    if cat_id is None:
        cat_id = get_category_id_by_name("Uncategorized", db_path)

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            UPDATE transactions
            SET tx_date = ?, description = ?, amount = ?, account = ?, category_id = ?, tags = ?
            WHERE id = ?
            """,
            (iso_date, desc, float(amount), str(account).strip(), cat_id, str(tags).strip(), int(tx_id))
        )
        conn.commit()
        return True, "Transaction updated successfully."
    except Exception as e:
        return False, f"Failed to update transaction: {str(e)}"
    finally:
        conn.close()


def delete_transaction(tx_id: int, db_path: str = DEFAULT_DB_PATH) -> Tuple[bool, str]:
    """
    Delete a single transaction by ID.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (int(tx_id),))
        conn.commit()
        if cursor.rowcount > 0:
            return True, "Transaction deleted successfully."
        return False, "Transaction ID not found."
    except Exception as e:
        return False, f"Error deleting transaction: {str(e)}"
    finally:
        conn.close()


def get_all_transactions_df(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Retrieve all transactions with joined category names, ordered by date descending.
    """
    conn = get_connection(db_path)
    query = """
    SELECT
        t.id,
        t.tx_date,
        t.description,
        t.amount,
        t.currency,
        t.account,
        COALESCE(c.name, 'Uncategorized') AS category,
        t.category_id,
        t.raw_source,
        t.tags
    FROM transactions t
    LEFT JOIN categories c ON t.category_id = c.id
    ORDER BY t.tx_date DESC, t.id DESC
    """
    try:
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()
