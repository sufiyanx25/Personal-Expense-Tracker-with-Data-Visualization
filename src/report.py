"""
report.py - Multi-Sheet Excel Financial Reporting Engine
=========================================================
Generates executive-ready Microsoft Excel workbooks using OpenPyXL with 4 structured sheets:
Sheet 1: Transactions (Date, Description, Amount, Account, Category, Currency)
Sheet 2: Category Summary (Category, Total Spending, Percentage of Total Spending)
Sheet 3: Monthly Summary (Total Income, Total Expenses, Savings, Savings Rate)
Sheet 4: Budget Summary (Category, Budget Limit, Actual Spending, Remaining Budget, Status)
"""

import os
import io
from datetime import datetime
from typing import Optional, Dict, Any, Union
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .analyze import get_financial_kpis, get_category_breakdown, get_monthly_summary
from .budget import get_budget_status
from .models import DEFAULT_DB_PATH

DEFAULT_OUTPUTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs"
)

# Corporate Navy Blue Palette for Worksheets
HEADER_FILL = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="1F497D")
SUBTITLE_FONT = Font(name="Calibri", size=10, italic=True, color="595959")
BOLD_FONT = Font(name="Calibri", size=11, bold=True)
REGULAR_FONT = Font(name="Calibri", size=11)

THIN_BORDER = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9")
)

TOTAL_BORDER = Border(
    top=Side(style="thin", color="000000"),
    bottom=Side(style="double", color="000000")
)

INR_FORMAT = '[$₹-4009] #,##0.00;([$₹-4009] #,##0.00);"-"'
PERCENT_FORMAT = '0.00%'


def _autofit_columns(ws, min_width: int = 12, padding: int = 4):
    """Dynamically adjust column widths based on maximum string lengths."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # Skip title merged cells in length calculation
            if cell.row in [1, 2]:
                continue
            if cell.value:
                val_str = str(cell.value)
                max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + padding, min_width)


def generate_monthly_excel_report(
    month: str,
    transactions_df: pd.DataFrame,
    output_path: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> Union[str, io.BytesIO]:
    """
    Generate an executive multi-sheet Excel report for a target month (YYYY-MM).
    If output_path is provided, saves to disk and returns file path string.
    If output_path is None, returns a BytesIO buffer suitable for Streamlit download.
    """
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    month_clean = str(month).strip()

    # Filter transactions for specified month
    if not transactions_df.empty and "tx_date" in transactions_df.columns:
        month_tx = transactions_df[
            transactions_df["tx_date"].astype(str).str.startswith(month_clean)
        ].copy()
    else:
        month_tx = pd.DataFrame(columns=[
            "tx_date", "description", "amount", "account", "category", "currency"
        ])

    # =========================================================================
    # Sheet 1: Transactions
    # =========================================================================
    ws1 = wb.create_sheet(title="Transactions")
    ws1.views.sheetView[0].showGridLines = True

    ws1["A1"] = f"Personal Expense Tracker - Transactions Register ({month_clean})"
    ws1["A1"].font = TITLE_FONT
    ws1["A2"] = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Currency: INR (₹)"
    ws1["A2"].font = SUBTITLE_FONT

    headers1 = ["Date", "Description", "Amount", "Account", "Category", "Currency"]
    ws1.append([])  # Row 3 blank
    ws1.append(headers1)  # Row 4

    for col_idx in range(1, len(headers1) + 1):
        cell = ws1.cell(row=4, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_idx = 5
    if not month_tx.empty:
        # Sort by date
        sorted_tx = month_tx.sort_values(by="tx_date", ascending=True)
        for _, tx in sorted_tx.iterrows():
            ws1.cell(row=row_idx, column=1, value=str(tx.get("tx_date", ""))).alignment = Alignment(horizontal="center")
            ws1.cell(row=row_idx, column=2, value=str(tx.get("description", ""))).alignment = Alignment(horizontal="left")
            
            amt_cell = ws1.cell(row=row_idx, column=3, value=float(tx.get("amount", 0.0)))
            amt_cell.number_format = INR_FORMAT
            amt_cell.alignment = Alignment(horizontal="right")
            
            ws1.cell(row=row_idx, column=4, value=str(tx.get("account", ""))).alignment = Alignment(horizontal="center")
            ws1.cell(row=row_idx, column=5, value=str(tx.get("category", "Uncategorized"))).alignment = Alignment(horizontal="left")
            ws1.cell(row=row_idx, column=6, value=str(tx.get("currency", "INR"))).alignment = Alignment(horizontal="center")

            for c in range(1, 7):
                ws1.cell(row=row_idx, column=c).border = THIN_BORDER
                ws1.cell(row=row_idx, column=c).font = REGULAR_FONT
            row_idx += 1
    else:
        ws1.cell(row=5, column=1, value="No transactions recorded for this month.").font = Font(italic=True, color="7F7F7F")

    _autofit_columns(ws1, min_width=14)

    # =========================================================================
    # Sheet 2: Category Summary
    # =========================================================================
    ws2 = wb.create_sheet(title="Category Summary")
    ws2.views.sheetView[0].showGridLines = True

    ws2["A1"] = f"Category-Wise Expense Breakdown ({month_clean})"
    ws2["A1"].font = TITLE_FONT
    ws2["A2"] = "Expenses only (Outflows) | Sorted by Total Spending"
    ws2["A2"].font = SUBTITLE_FONT

    headers2 = ["Category", "Total Spending", "Percentage of Total Spending"]
    ws2.append([])
    ws2.append(headers2)

    for col_idx in range(1, len(headers2) + 1):
        cell = ws2.cell(row=4, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    cat_summary = get_category_breakdown(month_tx)
    row_idx = 5
    if not cat_summary.empty:
        for _, c_row in cat_summary.iterrows():
            ws2.cell(row=row_idx, column=1, value=str(c_row["category"])).alignment = Alignment(horizontal="left")
            
            amt_cell = ws2.cell(row=row_idx, column=2, value=float(c_row["total_spending"]))
            amt_cell.number_format = INR_FORMAT
            amt_cell.alignment = Alignment(horizontal="right")
            
            pct_cell = ws2.cell(row=row_idx, column=3, value=float(c_row["percentage"]) / 100.0)
            pct_cell.number_format = PERCENT_FORMAT
            pct_cell.alignment = Alignment(horizontal="right")

            for c in range(1, 4):
                ws2.cell(row=row_idx, column=c).border = THIN_BORDER
                ws2.cell(row=row_idx, column=c).font = REGULAR_FONT
            row_idx += 1

        # Total Row
        ws2.cell(row=row_idx, column=1, value="Total Expenses").font = BOLD_FONT
        tot_cell = ws2.cell(row=row_idx, column=2, value=float(cat_summary["total_spending"].sum()))
        tot_cell.font = BOLD_FONT
        tot_cell.number_format = INR_FORMAT
        
        tot_pct = ws2.cell(row=row_idx, column=3, value=1.0)
        tot_pct.font = BOLD_FONT
        tot_pct.number_format = PERCENT_FORMAT

        for c in range(1, 4):
            ws2.cell(row=row_idx, column=c).border = TOTAL_BORDER
    else:
        ws2.cell(row=5, column=1, value="No expense records available for this month.").font = Font(italic=True, color="7F7F7F")

    _autofit_columns(ws2, min_width=20)

    # =========================================================================
    # Sheet 3: Monthly Summary
    # =========================================================================
    ws3 = wb.create_sheet(title="Monthly Summary")
    ws3.views.sheetView[0].showGridLines = True

    ws3["A1"] = "Executive Monthly Financial Summary"
    ws3["A1"].font = TITLE_FONT
    ws3["A2"] = "Historical Month-by-Month Trajectory & Savings Metrics"
    ws3["A2"].font = SUBTITLE_FONT

    headers3 = ["Month", "Total Income", "Total Expenses", "Savings", "Savings Rate"]
    ws3.append([])
    ws3.append(headers3)

    for col_idx in range(1, len(headers3) + 1):
        cell = ws3.cell(row=4, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    monthly_summary = get_monthly_summary(transactions_df)
    row_idx = 5
    if not monthly_summary.empty:
        for _, m_row in monthly_summary.iterrows():
            ws3.cell(row=row_idx, column=1, value=str(m_row["month"])).alignment = Alignment(horizontal="center")
            
            inc_cell = ws3.cell(row=row_idx, column=2, value=float(m_row["income"]))
            inc_cell.number_format = INR_FORMAT
            inc_cell.alignment = Alignment(horizontal="right")
            
            exp_cell = ws3.cell(row=row_idx, column=3, value=float(m_row["expenses"]))
            exp_cell.number_format = INR_FORMAT
            exp_cell.alignment = Alignment(horizontal="right")
            
            sav_cell = ws3.cell(row=row_idx, column=4, value=float(m_row["savings"]))
            sav_cell.number_format = INR_FORMAT
            sav_cell.alignment = Alignment(horizontal="right")
            
            rate_cell = ws3.cell(row=row_idx, column=5, value=float(m_row["savings_rate"]) / 100.0)
            rate_cell.number_format = PERCENT_FORMAT
            rate_cell.alignment = Alignment(horizontal="right")

            for c in range(1, 6):
                ws3.cell(row=row_idx, column=c).border = THIN_BORDER
                ws3.cell(row=row_idx, column=c).font = REGULAR_FONT
            row_idx += 1
    else:
        ws3.cell(row=5, column=1, value="No monthly summary data available.").font = Font(italic=True, color="7F7F7F")

    _autofit_columns(ws3, min_width=18)

    # =========================================================================
    # Sheet 4: Budget Summary
    # =========================================================================
    ws4 = wb.create_sheet(title="Budget Summary")
    ws4.views.sheetView[0].showGridLines = True

    ws4["A1"] = f"Budget vs Actual Variance Report ({month_clean})"
    ws4["A1"].font = TITLE_FONT
    ws4["A2"] = "Category Spending Limits, Actuals & Status Tracking"
    ws4["A2"].font = SUBTITLE_FONT

    headers4 = ["Category", "Budget Limit", "Actual Spending", "Remaining Budget", "Status"]
    ws4.append([])
    ws4.append(headers4)

    for col_idx in range(1, len(headers4) + 1):
        cell = ws4.cell(row=4, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")

    budget_status = get_budget_status(month_clean, transactions_df, db_path=db_path)
    row_idx = 5
    if not budget_status.empty:
        for _, b_row in budget_status.iterrows():
            ws4.cell(row=row_idx, column=1, value=str(b_row["category"])).alignment = Alignment(horizontal="left")
            
            b_limit = ws4.cell(row=row_idx, column=2, value=float(b_row["budget_limit"]))
            b_limit.number_format = INR_FORMAT
            b_limit.alignment = Alignment(horizontal="right")
            
            b_actual = ws4.cell(row=row_idx, column=3, value=float(b_row["actual_spending"]))
            b_actual.number_format = INR_FORMAT
            b_actual.alignment = Alignment(horizontal="right")
            
            b_rem = ws4.cell(row=row_idx, column=4, value=float(b_row["remaining_budget"]))
            b_rem.number_format = INR_FORMAT
            b_rem.alignment = Alignment(horizontal="right")
            
            status_str = str(b_row["status"])
            stat_cell = ws4.cell(row=row_idx, column=5, value=status_str)
            stat_cell.alignment = Alignment(horizontal="center")
            
            if status_str == "Budget Exceeded":
                stat_cell.font = Font(name="Calibri", size=11, bold=True, color="9C0006")
                stat_cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
            elif status_str == "Approaching Budget":
                stat_cell.font = Font(name="Calibri", size=11, bold=True, color="9C6500")
                stat_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
            else:
                stat_cell.font = Font(name="Calibri", size=11, color="006100")
                stat_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

            for c in range(1, 6):
                ws4.cell(row=row_idx, column=c).border = THIN_BORDER
                if c != 5:
                    ws4.cell(row=row_idx, column=c).font = REGULAR_FONT
            row_idx += 1
    else:
        ws4.cell(row=5, column=1, value=f"No budget targets configured for {month_clean}.").font = Font(italic=True, color="7F7F7F")

    _autofit_columns(ws4, min_width=18)

    # Export destination
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        wb.save(output_path)
        return output_path
    else:
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf
