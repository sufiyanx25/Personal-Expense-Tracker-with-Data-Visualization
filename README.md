# Personal Expense Tracker with Data Visualization

An industry-grade personal finance management and analytics platform engineered in Python, SQLite, and Streamlit.

---

## 1. Features

- **Local & Private Storage**: Uses SQLite with foreign key constraints, indexing, and duplicate detection. No external banking credentials required.
- **Dual-Channel Ingestion**: Upload bank/UPI statements via CSV with automated column mapping, or add manual cash and card transactions.
- **Automated Categorization**: Keyword-based rule engine tailored for Indian transactions (Swiggy, DMart, Uber, BESCOM, etc.).
- **Interactive Visual Analytics**: Plotly charts for category spending, monthly trends, payment method share, and daily spending velocity.
- **Budget Control & Alerts**: Monthly category budget targets with real-time overspending alerts (`Within Budget`, `Approaching Budget`, `Budget Exceeded`).
- **Multi-Sheet Excel Reports**: Generates executive `.xlsx` workbooks with OpenPyXL formatted in Indian Rupees (₹).
- **Transaction Management**: Search, filter, edit, and delete transactions with confirmation protection.

---

## 2. Technology Stack

- **Language**: Python 3.11 / 3.12
- **Data & Computation**: Pandas, NumPy
- **Database**: SQLite (built-in standard library `sqlite3`)
- **Web Dashboard**: Streamlit
- **Visualizations**: Plotly, Matplotlib
- **Excel Reporting**: OpenPyXL
- **Machine Learning (Optional)**: Scikit-learn

---

## 3. Project Structure

```
Personal-Expense-Tracker/
│
├── data/
│   └── sample_expenses.csv       # Synthetic Indian personal finance dataset
│
├── db/
│   ├── .gitkeep
│   └── expenses.db               # SQLite transactional database
│
├── outputs/
│   ├── .gitkeep
│   └── Financial_Report_*.xlsx   # Generated Excel reports
│
├── src/
│   ├── __init__.py               # Package marker
│   ├── models.py                 # SQLite schema, connection factory & CRUD helpers
│   ├── ingest.py                 # CSV ingestion, data validation & manual entry
│   ├── categorize.py             # Keyword rule-based categorization engine
│   ├── analyze.py                # Financial KPI calculations & aggregations
│   ├── budget.py                 # Monthly budget tracking & threshold alerts
│   ├── plots.py                  # Interactive Plotly & static Matplotlib figures
│   ├── report.py                 # Multi-sheet OpenPyXL Excel export engine
│   └── app_streamlit.py          # Interactive Streamlit dashboard
│
├── README.md                     # Project documentation
├── requirements.txt              # Project dependencies
├── .gitignore                    # Git exclusions
└── main.py                       # CLI application orchestrator
```

---

## 4. Installation

### 1. Clone or Open the Repository
```bash
cd "Personal Expense Tracker with Data Visualization"
```

### 2. Create and Activate Virtual Environment (Recommended)
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 5. How to Run

### Primary Method: Launch Streamlit Web Dashboard
```bash
streamlit run src/app_streamlit.py
```
*(Or run `py -3.12 -m streamlit run src/app_streamlit.py`)*

The dashboard will automatically open in your browser at `http://localhost:8501`.

### Secondary Method: CLI Commands (`main.py`)
```bash
# Launch dashboard
python main.py

# Initialize database schema & seed sample data
python main.py --init-db

# Display console financial summary
python main.py --summary

# Ingest an external CSV statement
python main.py --import-csv data/sample_expenses.csv

# Generate monthly Excel report (e.g., for October 2024)
python main.py --report 2024-10
```

---

## 6. Sample CSV Format

The application accepts CSV statement exports with these standard fields:

| Field | Format / Example | Description |
| :--- | :--- | :--- |
| `tx_date` | `2024-10-15` | Date formatted as `YYYY-MM-DD` |
| `description` | `Swiggy Food Delivery` | Transaction description / merchant narrative |
| `amount` | `-540.00` / `85000.00` | Negative for expenses, positive for income |
| `account` | `UPI`, `Debit Card`, `Credit Card`, `Cash` | Payment mode |
| `raw_source` | `BANK_STATEMENT`, `UPI_APP`, `MANUAL` | Provenance identifier |

---

## 7. Excel Report Contents

Generated via the **Reports & Export** tab in the dashboard or CLI:
- **Sheet 1: Transactions** — Complete itemized log with currency, account, and category.
- **Sheet 2: Category Summary** — Spending totals, category share percentages, and total expenses.
- **Sheet 3: Monthly Summary** — Inflow, Outflow, Net Savings, and Savings Rate.
- **Sheet 4: Budget Summary** — Budget limits vs. actuals with color-coded status (`SAFE`, `WARNING`, `EXCEEDED`).

---

## 8. Git & GitHub Setup

```bash
git init
git add .
git commit -m "feat: complete personal expense tracker with data visualization"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```
