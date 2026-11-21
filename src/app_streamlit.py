"""
app_streamlit.py - Interactive Personal Finance Dashboard
=========================================================
Delivers a responsive Streamlit web application featuring:
1. Executive Overview with KPI Scorecards and Quick Visuals.
2. Form-based Manual Transaction Entry with automatic sign enforcement.
3. CSV Statement Import with duplicate prevention and validation preview.
4. Searchable & Filterable Transaction History with Edit and Delete controls.
5. In-depth Analytics rendering all 4 required charts and spending distributions.
6. Budget Management with variance tracking and automated threshold alerts.
7. Executive-grade multi-sheet OpenPyXL Excel report downloads.
"""

import os
import sys
from datetime import date, datetime
import pandas as pd
import streamlit as st

# Ensure repository root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    add_manual_transaction,
    update_transaction,
    delete_transaction,
    get_all_transactions_df
)
from src.analyze import (
    get_financial_kpis,
    get_monthly_summary,
    get_category_breakdown,
    get_payment_method_breakdown,
    get_daily_spending_trend
)
from src.budget import (
    set_budget,
    get_all_budgets,
    delete_budget,
    get_budget_status,
    get_overspending_alerts
)
from src.plots import (
    plot_category_bar,
    plot_monthly_trend_line,
    plot_payment_method_pie,
    plot_daily_trend,
    plot_income_vs_expense,
    plot_budget_vs_actual,
    plot_category_donut
)
from src.report import generate_monthly_excel_report


# ============================================================================
# Page Configuration & Corporate Custom CSS
# ============================================================================

st.set_page_config(
    page_title="Personal Expense Tracker | Analytics Dashboard",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    /* Metric Card Styling */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        font-weight: 600;
        color: #475569;
    }
    .kpi-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-safe {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-warning {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-danger {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================================
# Automatic Database & Seed Initialization
# ============================================================================

def ensure_initialized():
    """Ensure database schema is ready and seed initial sample data if empty."""
    init_db(DEFAULT_DB_PATH)
    conn = get_connection(DEFAULT_DB_PATH)
    try:
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        if count == 0:
            sample_csv = os.path.join(BASE_DIR, "data", "sample_expenses.csv")
            if os.path.exists(sample_csv):
                import_csv_to_db(sample_csv, DEFAULT_DB_PATH)
                # Seed default monthly budgets for testing
                set_budget("2024-10", "Food & Dining", 8000.00, DEFAULT_DB_PATH)
                set_budget("2024-10", "Groceries", 12000.00, DEFAULT_DB_PATH)
                set_budget("2024-10", "Transport", 6000.00, DEFAULT_DB_PATH)
                set_budget("2024-10", "Shopping", 8000.00, DEFAULT_DB_PATH)
                set_budget("2024-10", "Bills & Utilities", 7000.00, DEFAULT_DB_PATH)
                set_budget("2024-11", "Food & Dining", 8000.00, DEFAULT_DB_PATH)
                set_budget("2024-11", "Groceries", 12000.00, DEFAULT_DB_PATH)
                set_budget("2024-11", "Transport", 6000.00, DEFAULT_DB_PATH)
    finally:
        conn.close()

ensure_initialized()


# ============================================================================
# Sidebar Navigation and Global Context
# ============================================================================

st.sidebar.title("💳 Expense Tracker")
st.sidebar.caption("Personal Finance & Analytics Platform")

# Load existing transactions to obtain available months
all_tx_df = get_all_transactions_df(DEFAULT_DB_PATH)

available_months = ["All Months"]
if not all_tx_df.empty and "tx_date" in all_tx_df.columns:
    months_series = sorted(all_tx_df["tx_date"].astype(str).str.slice(0, 7).unique(), reverse=True)
    available_months.extend(months_series)

st.sidebar.markdown("---")
st.sidebar.subheader("Navigation")
menu_selection = st.sidebar.radio(
    "Go to",
    [
        "📊 Overview",
        "➕ Add Transaction",
        "📥 Import CSV",
        "📋 Transaction History",
        "📈 Analytics & Charts",
        "🎯 Budget Management",
        "📄 Reports & Export"
    ],
    index=0
)

st.sidebar.markdown("---")
selected_month_filter = st.sidebar.selectbox(
    "Active Month Filter",
    options=available_months,
    index=0,
    help="Filters metrics and charts across Overview, Analytics, and Reports."
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Privacy First**: All financial data is stored locally in SQLite (`db/expenses.db`). "
    "No bank credentials or external APIs required."
)


def safe_render_dataframe(df, use_container_width=True, height=None):
    """Safely render DataFrame with automatic fallback to st.table if PyArrow fails."""
    try:
        if height:
            st.dataframe(df, use_container_width=use_container_width, height=height)
        else:
            st.dataframe(df, use_container_width=use_container_width)
    except Exception:
        st.table(df)


# Filtered transaction slice based on sidebar month
if selected_month_filter != "All Months" and not all_tx_df.empty:
    active_df = all_tx_df[all_tx_df["tx_date"].astype(str).str.startswith(selected_month_filter)].copy()
else:
    active_df = all_tx_df.copy()


# ============================================================================
# Section A: Overview
# ============================================================================

if menu_selection == "📊 Overview":
    st.header(f"📊 Financial Overview {f'({selected_month_filter})' if selected_month_filter != 'All Months' else '(All Time)'}")
    
    kpis = get_financial_kpis(active_df)

    # Top KPI Scorecards
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="Total Income",
            value=f"₹{kpis['total_income']:,.2f}",
            delta=None
        )
    with col2:
        st.metric(
            label="Total Expenses",
            value=f"₹{kpis['total_expenses']:,.2f}",
            delta=None
        )
    with col3:
        savings_color = "normal" if kpis["total_savings"] >= 0 else "inverse"
        st.metric(
            label="Net Savings",
            value=f"₹{kpis['total_savings']:,.2f}",
            delta=f"{kpis['savings_rate']:.1f}% Rate" if kpis["total_income"] > 0 else None
        )
    with col4:
        st.metric(
            label="Savings Rate",
            value=f"{kpis['savings_rate']:.1f}%",
            delta=None
        )
    with col5:
        st.metric(
            label="Top Spending Category",
            value=kpis["highest_spending_category"],
            delta=f"₹{kpis['highest_spending_amount']:,.2f}" if kpis["highest_spending_amount"] > 0 else None
        )

    st.markdown("---")

    # High-level Visuals
    c1, c2 = st.columns(2)
    with c1:
        cat_df = get_category_breakdown(active_df)
        st.plotly_chart(plot_category_donut(cat_df), use_container_width=True)

    with c2:
        monthly_df = get_monthly_summary(all_tx_df)
        st.plotly_chart(plot_income_vs_expense(monthly_df), use_container_width=True)

    st.markdown("---")
    st.subheader("Recent Transactions")
    if not active_df.empty:
        display_recent = active_df.head(10)[["tx_date", "description", "amount", "account", "category", "raw_source"]].copy()
        display_recent["amount"] = display_recent["amount"].apply(lambda x: f"₹{x:,.2f}")
        safe_render_dataframe(display_recent, use_container_width=True)
    else:
        st.info("No transaction records found. Use 'Add Transaction' or 'Import CSV' to get started.")


# ============================================================================
# Section B: Add Transaction
# ============================================================================

elif menu_selection == "➕ Add Transaction":
    st.header("➕ Add Transaction")
    st.caption("Record a manual expenditure or income credit.")

    db_categories = get_categories(DEFAULT_DB_PATH)
    category_options = ["Auto (Rule-Based)"] + [c["name"] for c in db_categories]

    with st.form("manual_tx_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tx_date_input = st.date_input("Transaction Date", value=date.today())
            description_input = st.text_input("Description / Narrative", placeholder="e.g., Grocery shopping at DMart")
            amount_input = st.number_input("Amount (₹ INR)", min_value=0.01, step=10.0, format="%.2f")

        with col2:
            tx_type = st.radio("Transaction Type", ["Expense", "Income"], horizontal=True)
            account_input = st.selectbox(
                "Payment Account / Method",
                ["UPI", "Debit Card", "Credit Card", "Cash", "Net Banking"]
            )
            selected_cat = st.selectbox("Category", category_options, index=0)
            tags_input = st.text_input("Optional Tags / Notes", placeholder="e.g., Personal, Office, Reimbursement")

        submitted = st.form_submit_button("💾 Save Transaction", use_container_width=True)

        if submitted:
            cat_to_pass = None if selected_cat == "Auto (Rule-Based)" else selected_cat
            success, msg, new_id = add_manual_transaction(
                tx_date=tx_date_input.strftime("%Y-%m-%d"),
                description=description_input,
                amount=amount_input,
                transaction_type=tx_type,
                account=account_input,
                category_name=cat_to_pass,
                tags=tags_input,
                db_path=DEFAULT_DB_PATH
            )
            if success:
                st.success(f"✅ {msg} (Record ID: {new_id})")
                st.toast(f"Transaction #{new_id} recorded successfully!", icon="✅")
            else:
                st.error(f"❌ {msg}")


# ============================================================================
# Section C: Import CSV
# ============================================================================

elif menu_selection == "📥 Import CSV":
    st.header("📥 Import CSV Bank / Statement File")
    st.caption("Upload a statement CSV to automatically validate, categorize, and store transactions.")

    uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            preview_df = pd.read_csv(uploaded_file)
            uploaded_file.seek(0)
            st.subheader("File Preview (Top 5 Rows)")
            safe_render_dataframe(preview_df.head(5), use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Total Rows in File**: {len(preview_df)}")
                st.write(f"**Detected Columns**: `{', '.join(preview_df.columns)}`")
            with col2:
                st.info("The importer automatically maps common aliases for date, description, amount, account, and category.")

            if st.button("🚀 Ingest & Categorize Transactions", use_container_width=True):
                with st.spinner("Processing transactions and checking duplicates..."):
                    result = import_csv_to_db(uploaded_file, DEFAULT_DB_PATH)
                    if result["success"]:
                        st.success(
                            f"🎉 Successfully imported **{result['imported']}** new transactions! "
                            f"(Skipped **{result['duplicates']}** duplicate records)."
                        )
                        if result["errors"]:
                            st.warning("Validation notices:\n" + "\n".join(f"- {e}" for e in result["errors"]))
                        st.rerun()
                    else:
                        st.error("Failed to import CSV:\n" + "\n".join(f"- {e}" for e in result["errors"]))
        except Exception as e:
            st.error(f"Could not parse uploaded CSV: {str(e)}")

    st.markdown("---")
    st.subheader("Supported CSV Format Guidelines")
    st.markdown("""
    Ensure your CSV includes at least the following columns:
    - **tx_date**: Date formatted as `YYYY-MM-DD` (or `DD-MM-YYYY`).
    - **description**: Transaction narrative or merchant name.
    - **amount**: Positive for income, negative for expenses (or absolute with type).
    - **account**: Payment mode (`UPI`, `Debit Card`, `Credit Card`, `Cash`).
    - **category** *(optional)*: Auto-classified by keyword rules if omitted.
    """)


# ============================================================================
# Section D: Transaction History
# ============================================================================

elif menu_selection == "📋 Transaction History":
    st.header("📋 Transaction History & Management")
    st.caption("Filter, search, inspect, edit, or delete transactions.")

    if all_tx_df.empty:
        st.info("No transactions found in database.")
    else:
        # Filter Bar
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            search_query = st.text_input("🔍 Search Description/Tags", "")
        with fcol2:
            type_filter = st.selectbox("Type", ["All", "Expenses Only", "Income Only"])
        with fcol3:
            all_cats = ["All"] + sorted(all_tx_df["category"].dropna().unique().tolist())
            cat_filter = st.selectbox("Category", all_cats)
        with fcol4:
            all_accs = ["All"] + sorted(all_tx_df["account"].dropna().unique().tolist())
            acc_filter = st.selectbox("Account", all_accs)

        # Apply Filters
        filtered_df = all_tx_df.copy()
        if search_query.strip():
            q = search_query.strip().lower()
            filtered_df = filtered_df[
                filtered_df["description"].str.lower().str.contains(q, na=False) |
                filtered_df["tags"].str.lower().str.contains(q, na=False)
            ]
        if type_filter == "Expenses Only":
            filtered_df = filtered_df[filtered_df["amount"] < 0]
        elif type_filter == "Income Only":
            filtered_df = filtered_df[filtered_df["amount"] > 0]
        if cat_filter != "All":
            filtered_df = filtered_df[filtered_df["category"] == cat_filter]
        if acc_filter != "All":
            filtered_df = filtered_df[filtered_df["account"] == acc_filter]

        st.write(f"Showing **{len(filtered_df)}** of **{len(all_tx_df)}** transactions")

        # Table Display
        display_table = filtered_df[["id", "tx_date", "description", "amount", "account", "category", "tags"]].copy()
        safe_render_dataframe(display_table, use_container_width=True, height=360)

        st.markdown("---")
        # Edit and Delete Sub-Tabs
        tab_edit, tab_del = st.tabs(["✏️ Edit Transaction", "🗑️ Delete Transaction"])

        with tab_edit:
            st.subheader("Edit Existing Transaction")
            selected_tx_id = st.selectbox(
                "Select Transaction ID to Edit",
                options=filtered_df["id"].tolist(),
                key="edit_tx_id_select"
            )
            if selected_tx_id:
                tx_row = all_tx_df[all_tx_df["id"] == selected_tx_id].iloc[0]
                with st.form("edit_tx_form"):
                    ecol1, ecol2 = st.columns(2)
                    with ecol1:
                        e_date = st.date_input("Date", value=datetime.strptime(tx_row["tx_date"], "%Y-%m-%d").date())
                        e_desc = st.text_input("Description", value=tx_row["description"])
                        e_amt = st.number_input("Amount (₹ INR)", value=float(tx_row["amount"]), step=10.0, format="%.2f")
                    with ecol2:
                        e_acc = st.selectbox("Account", ["UPI", "Debit Card", "Credit Card", "Cash", "Net Banking"],
                                             index=["UPI", "Debit Card", "Credit Card", "Cash", "Net Banking"].index(tx_row["account"]) if tx_row["account"] in ["UPI", "Debit Card", "Credit Card", "Cash", "Net Banking"] else 0)
                        
                        db_categories = get_categories(DEFAULT_DB_PATH)
                        cat_names = [c["name"] for c in db_categories]
                        curr_cat_idx = cat_names.index(tx_row["category"]) if tx_row["category"] in cat_names else 0
                        e_cat = st.selectbox("Category", cat_names, index=curr_cat_idx)
                        e_tags = st.text_input("Tags / Notes", value=str(tx_row.get("tags", "")))

                    edit_submitted = st.form_submit_button("Update Transaction", use_container_width=True)
                    if edit_submitted:
                        ok, msg = update_transaction(
                            tx_id=selected_tx_id,
                            tx_date=e_date.strftime("%Y-%m-%d"),
                            description=e_desc,
                            amount=e_amt,
                            account=e_acc,
                            category_name=e_cat,
                            tags=e_tags,
                            db_path=DEFAULT_DB_PATH
                        )
                        if ok:
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

        with tab_del:
            st.subheader("Delete Transaction")
            del_id = st.selectbox("Select Transaction ID to Delete", options=filtered_df["id"].tolist(), key="del_tx_id_select")
            if del_id:
                del_row = all_tx_df[all_tx_df["id"] == del_id].iloc[0]
                st.warning(f"Are you sure you want to delete Transaction #{del_id}: **{del_row['description']}** (₹{del_row['amount']:,.2f}) on {del_row['tx_date']}?")
                confirm_del = st.checkbox("Yes, permanently delete this transaction record.", key="confirm_del_check")
                if st.button("🚨 Confirm Delete", disabled=not confirm_del, type="primary"):
                    ok, msg = delete_transaction(del_id, DEFAULT_DB_PATH)
                    if ok:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")


# ============================================================================
# Section E: Analytics & Charts
# ============================================================================

elif menu_selection == "📈 Analytics & Charts":
    st.header(f"📈 Analytics & Charts {f'({selected_month_filter})' if selected_month_filter != 'All Months' else '(All Time)'}")
    
    # 4 Required Visualizations:
    # 1. Category-wise spending bar chart
    # 2. Monthly spending trend line chart
    # 3. Payment-method distribution pie chart
    # 4. Daily spending trend chart

    cat_df = get_category_breakdown(active_df)
    monthly_df = get_monthly_summary(all_tx_df)
    acc_df = get_payment_method_breakdown(active_df)
    daily_df = get_daily_spending_trend(active_df)

    tab1, tab2 = st.tabs(["📊 Required Charts (1-4)", "🔍 Deep Dive Visualizations"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(plot_category_bar(cat_df), use_container_width=True)
        with c2:
            st.plotly_chart(plot_monthly_trend_line(monthly_df), use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(plot_payment_method_pie(acc_df), use_container_width=True)
        with c4:
            st.plotly_chart(plot_daily_trend(daily_df), use_container_width=True)

    with tab2:
        st.subheader("Monthly Income vs Expense Comparison")
        st.plotly_chart(plot_income_vs_expense(monthly_df), use_container_width=True)

        st.subheader("Category Expenditure Shares")
        st.plotly_chart(plot_category_donut(cat_df), use_container_width=True)


# ============================================================================
# Section F: Budget Management
# ============================================================================

elif menu_selection == "🎯 Budget Management":
    st.header("🎯 Monthly Budget Planner & Overspending Tracker")
    st.caption("Allocate category spending targets, review utilization, and monitor threshold alerts.")

    # Target Month Selector for Budgeting
    budget_target_month = st.selectbox(
        "Select Target Month for Budgeting",
        options=[m for m in available_months if m != "All Months"] or [datetime.now().strftime("%Y-%m")],
        index=0
    )

    # Overspending & Warning Alerts
    status_df = get_budget_status(budget_target_month, all_tx_df, DEFAULT_DB_PATH)
    alerts = get_overspending_alerts(status_df)

    if alerts:
        st.subheader("⚠️ Budget Alerts")
        for alert in alerts:
            if alert["type"] == "error":
                st.error(alert["message"])
            else:
                st.warning(alert["message"])
    elif not status_df.empty:
        st.success("🎉 Excellent! All categories are currently operating safely within budget limits.")

    st.markdown("---")

    col_view, col_form = st.columns([3, 2])

    with col_view:
        st.subheader(f"Budget Status for {budget_target_month}")
        if not status_df.empty:
            display_budget = status_df[["category", "budget_limit", "actual_spending", "remaining_budget", "utilization_percent", "status"]].copy()
            safe_render_dataframe(display_budget, use_container_width=True)
            st.plotly_chart(plot_budget_vs_actual(status_df), use_container_width=True)
        else:
            st.info(f"No budgets defined for {budget_target_month}. Use the form on the right to set targets.")

    with col_form:
        st.subheader("Set / Update Budget")
        db_categories = get_categories(DEFAULT_DB_PATH)
        expense_cats = [c["name"] for c in db_categories if c.get("parent") != "Income"]

        with st.form("budget_form"):
            b_month = st.text_input("Month (YYYY-MM)", value=budget_target_month)
            b_cat = st.selectbox("Category", expense_cats)
            b_limit = st.number_input("Budget Limit (₹ INR)", min_value=100.0, step=500.0, value=5000.0)

            b_submit = st.form_submit_button("Save Budget Limit", use_container_width=True)
            if b_submit:
                ok, msg = set_budget(b_month, b_cat, b_limit, DEFAULT_DB_PATH)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        # Delete Budget Option
        all_budgets = get_all_budgets(DEFAULT_DB_PATH)
        if not all_budgets.empty:
            st.markdown("---")
            st.subheader("Remove Budget Target")
            b_choices = {f"#{row['id']}: {row['month']} - {row['category_name']} (₹{row['limit_amount']:,.0f})": row['id']
                         for _, row in all_budgets.iterrows()}
            selected_b_str = st.selectbox("Select Budget to Remove", options=list(b_choices.keys()))
            if st.button("Delete Selected Budget", type="secondary"):
                b_id_to_del = b_choices[selected_b_str]
                ok, msg = delete_budget(b_id_to_del, DEFAULT_DB_PATH)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")


# ============================================================================
# Section G: Reports & Export
# ============================================================================

elif menu_selection == "📄 Reports & Export":
    st.header("📄 Executive Financial Reports & Export")
    st.caption("Generate downloadable multi-sheet Microsoft Excel workbooks formatted in INR (₹).")

    report_month = st.selectbox(
        "Select Target Report Month",
        options=[m for m in available_months if m != "All Months"] or [datetime.now().strftime("%Y-%m")],
        index=0
    )

    kpi_report = get_financial_kpis(all_tx_df[all_tx_df["tx_date"].astype(str).str.startswith(report_month)])

    st.subheader(f"Summary for {report_month}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Inflow (Income)", f"₹{kpi_report['total_income']:,.2f}")
    c2.metric("Outflow (Expenses)", f"₹{kpi_report['total_expenses']:,.2f}")
    c3.metric("Net Savings", f"₹{kpi_report['total_savings']:,.2f}")
    c4.metric("Savings Ratio", f"{kpi_report['savings_rate']:.1f}%")

    st.markdown("---")
    st.write("### Excel Workbook Contents:")
    st.markdown("""
    - **Sheet 1: Transactions** — Complete itemized transaction register for the month with currency, account, and category.
    - **Sheet 2: Category Summary** — Breakdown of total spending and percentage share by category.
    - **Sheet 3: Monthly Summary** — Executive historical trajectory comparing income, expenses, savings, and savings rate.
    - **Sheet 4: Budget Summary** — Actual spending compared to budget caps with color-coded alerts (`SAFE`, `WARNING`, `EXCEEDED`).
    """)

    excel_buffer = generate_monthly_excel_report(
        month=report_month,
        transactions_df=all_tx_df,
        output_path=None,
        db_path=DEFAULT_DB_PATH
    )

    filename = f"Personal_Expense_Report_{report_month}.xlsx"

    st.download_button(
        label=f"📥 Download Excel Report ({filename})",
        data=excel_buffer,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("Export All Transactions (CSV)")
    if not all_tx_df.empty:
        csv_data = all_tx_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Full Transaction Database (CSV)",
            data=csv_data,
            file_name="transactions_database.csv",
            mime="text/csv",
            use_container_width=True
        )
