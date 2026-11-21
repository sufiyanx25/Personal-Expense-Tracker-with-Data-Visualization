"""
main.py - Application Entry Point, Database Bootstrapper, and Orchestrator
==========================================================================
Bootstraps SQLite storage, seeds initial categories and sample datasets,
and provides execution routers for CLI operations and the Streamlit dashboard.

Primary Launch Command:
    streamlit run src/app_streamlit.py
Or:
    python main.py
"""

import os
import sys
import argparse
import subprocess

# Ensure repository root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.models import (
    init_db,
    get_connection,
    get_categories,
    DEFAULT_DB_PATH
)
from src.ingest import (
    import_csv_to_db,
    get_all_transactions_df
)
from src.analyze import (
    get_financial_kpis,
    get_monthly_summary,
    get_category_breakdown
)
from src.report import (
    generate_monthly_excel_report,
    DEFAULT_OUTPUTS_DIR
)


def bootstrap_environment(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Ensure all prerequisite directories exist, tables are created,
    and seed sample expenses if the database is newly initialized.
    """
    # 1. Ensure core directories
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "db"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "src"), exist_ok=True)

    # 2. Initialize database & default categories
    init_db(db_path)

    # 3. Seed sample data if empty
    conn = get_connection(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        if count == 0:
            sample_csv = os.path.join(BASE_DIR, "data", "sample_expenses.csv")
            if os.path.exists(sample_csv):
                print(f"[*] Seeding initial synthetic data from '{sample_csv}'...")
                res = import_csv_to_db(sample_csv, db_path)
                print(f"[+] Loaded {res['imported']} transactions successfully.")
    finally:
        conn.close()


def launch_dashboard() -> None:
    """Launch the interactive Streamlit dashboard."""
    bootstrap_environment()
    app_path = os.path.join(BASE_DIR, "src", "app_streamlit.py")
    print("=" * 70)
    print(" Personal Expense Tracker with Data Visualization")
    print(" Launching Streamlit Web Application...")
    print(f" Target Script: {app_path}")
    print("=" * 70)
    
    cmd = [sys.executable, "-m", "streamlit", "run", app_path]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[!] Dashboard shut down by user.")


def parse_arguments() -> argparse.Namespace:
    """Parse command line flags."""
    parser = argparse.ArgumentParser(
        description="Personal Expense Tracker with Data Visualization - CLI Orchestrator"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the interactive Streamlit web dashboard in your browser."
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize SQLite database tables, indexes, and default categories."
    )
    parser.add_argument(
        "--import-csv",
        type=str,
        metavar="CSV_PATH",
        help="Ingest and auto-categorize an external transaction CSV file."
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Compute and display an overall financial KPI summary in console."
    )
    parser.add_argument(
        "--report",
        type=str,
        metavar="YYYY-MM",
        help="Generate a comprehensive Excel workbook report for the specified month."
    )
    return parser.parse_args()


def main() -> None:
    """Main CLI entry point."""
    args = parse_arguments()

    if args.init_db:
        bootstrap_environment()
        print("[+] Database and categories initialized successfully.")
        return

    if args.import_csv:
        bootstrap_environment()
        print(f"[*] Importing CSV file: {args.import_csv}...")
        res = import_csv_to_db(args.import_csv)
        if res["success"]:
            print(f"[+] Successfully imported {res['imported']} rows (Skipped {res['duplicates']} duplicates).")
        else:
            print(f"[-] CSV import failed: {res['errors']}")
        return

    if args.summary:
        bootstrap_environment()
        df = get_all_transactions_df()
        kpis = get_financial_kpis(df)
        print("\n" + "=" * 50)
        print(" FINANCIAL SUMMARY OVERVIEW")
        print("=" * 50)
        print(f" Total Inflow (Income)   : ₹{kpis['total_income']:,.2f}")
        print(f" Total Outflow (Expenses): ₹{kpis['total_expenses']:,.2f}")
        print(f" Net Savings Balance     : ₹{kpis['total_savings']:,.2f}")
        print(f" Savings Ratio           : {kpis['savings_rate']:.2f}%")
        print(f" Top Outflow Category    : {kpis['highest_spending_category']} (₹{kpis['highest_spending_amount']:,.2f})")
        print(f" Average Daily Spend     : ₹{kpis['avg_daily_spending']:,.2f}")
        print(f" Total Transactions Logged: {kpis['transaction_count']}")
        print("=" * 50 + "\n")
        return

    if args.report:
        bootstrap_environment()
        df = get_all_transactions_df()
        out_file = os.path.join(DEFAULT_OUTPUTS_DIR, f"Financial_Report_{args.report}.xlsx")
        print(f"[*] Generating multi-sheet Excel report for month {args.report}...")
        path = generate_monthly_excel_report(args.report, df, output_path=out_file)
        print(f"[+] Report generated successfully at: {path}")
        return

    # Default action: launch Streamlit dashboard
    launch_dashboard()


if __name__ == "__main__":
    main()
