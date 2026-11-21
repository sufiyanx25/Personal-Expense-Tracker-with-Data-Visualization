"""
Personal Expense Tracker with Data Visualization
================================================
A modular, industry-standard personal finance management and analytics platform.

Core Modules:
-------------
- models: SQLite database schema, connections, and domain entities.
- ingest: CSV dataset ingestion, validation, and manual expense entries.
- categorize: Rule-based keyword matching and machine learning categorizer.
- analyze: Financial metric aggregation, monthly summaries, and savings calculations.
- budget: Monthly spending limits, alert thresholds, and variance analysis.
- plots: Interactive Plotly and static Matplotlib visualizations.
- report: Multi-sheet OpenPyXL Excel reporting engine.
- app_streamlit: Web-based interactive financial dashboard.

Version: 0.1.0 (PART 1 - Project Initialization & Architecture)
"""

__version__ = "0.1.0"
__author__ = "Personal Expense Tracker Architecture Team"

__all__ = [
    "models",
    "ingest",
    "categorize",
    "analyze",
    "budget",
    "plots",
    "report",
]
