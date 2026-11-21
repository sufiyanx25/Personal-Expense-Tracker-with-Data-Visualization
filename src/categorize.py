"""
categorize.py - Automatic Transaction Categorization Engine
===========================================================
Implements a keyword-based rule engine and optional Scikit-learn Naive Bayes
classification for automatic expense and income categorization.
"""

import re
from typing import Dict, List, Optional, Any
import pandas as pd
from .models import get_category_id_by_name, DEFAULT_DB_PATH

# Primary keyword mapping dictionary tailored to Indian personal finance
KEYWORD_RULES: Dict[str, List[str]] = {
    "Income": [
        "salary", "payroll", "stipend", "bonus", "freelance", "consulting",
        "dividend", "interest credit", "savings interest", "honorarium", "cashback", "refund"
    ],
    "Food & Dining": [
        "swiggy", "zomato", "restaurant", "cafe", "starbucks", "barista", "mcdonald",
        "kfc", "burger", "pizza", "dine", "lunch", "dinner", "breakfast", "snacks",
        "chai", "tea", "coffee", "bakery", "dhaba", "bistro", "barbeque", "biryani",
        "food", "eatery", "canteen", "haldiram"
    ],
    "Groceries": [
        "grocery", "groceries", "blinkit", "zepto", "instamart", "d-mart", "dmart",
        "bigbasket", "nature's basket", "kirana", "milk", "dairy", "eggs", "vegetable",
        "provisions", "supermarket", "ration", "fruits", "spices", "atta", "dal"
    ],
    "Transport": [
        "uber", "ola", "rapido", "metro", "fuel", "petrol", "diesel", "cng",
        "hpcl", "bpcl", "iocl", "shell", "fastag", "toll", "parking", "auto ride",
        "cab", "taxi", "commute", "car service", "bike service"
    ],
    "Bills & Utilities": [
        "electricity", "bescom", "tneb", "msedcl", "tata power", "adani electricity",
        "wifi", "broadband", "internet", "airtel", "jio", "vodafone", "vi",
        "recharge", "mobile bill", "lpg", "cylinder", "indane", "bharat gas", "hp gas",
        "water bill", "water tanker", "gas bill", "utility", "maintenance fee"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa", "zara", "h&m",
        "decathlon", "shopping", "clothes", "apparel", "electronics", "gadgets",
        "retail", "footwear", "lifestyle"
    ],
    "Entertainment": [
        "netflix", "spotify", "hotstar", "prime video", "sonyliv", "zee5",
        "bookmyshow", "pvr", "inox", "movie", "cinema", "concert", "game",
        "amusement", "theatre", "audible", "youtube premium"
    ],
    "Healthcare": [
        "pharmacy", "apollo", "medplus", "1mg", "pharmeasy", "doctor", "hospital",
        "clinic", "dental", "health", "medicine", "diagnostic", "lab", "consultation",
        "therapy", "insurance premium", "spectacles"
    ],
    "Education": [
        "fee", "school", "college", "tuition", "course", "udemy", "coursera",
        "books", "stationery", "exam", "coaching", "university", "admission"
    ],
    "Rent": [
        "house rent", "flat rent", "pg rent", "room rent", "rent payment", "landlord", "society maintenance"
    ],
    "Travel": [
        "flight", "airline", "indigo", "air india", "akasa", "spicejet", "train",
        "irctc", "bus", "redbus", "hotel", "makemytrip", "goibibo", "agoda",
        "booking.com", "trip", "resort", "vacation", "holiday", "homestay"
    ]
}


def rule_based_categorize(
    description: str,
    amount: Optional[float] = None,
    rules: Optional[Dict[str, List[str]]] = None
) -> str:
    """
    Categorize a transaction based on keywords and amount sign.
    Ensures positive amounts (income) are never labeled as an expense category.
    """
    if not description:
        return "Income" if (amount is not None and amount > 0) else "Uncategorized"

    text = description.lower()
    active_rules = rules if rules is not None else KEYWORD_RULES

    # If amount is strictly positive (income/credit), check income keywords first
    if amount is not None and amount > 0:
        for kw in active_rules.get("Income", []):
            if re.search(r"\b" + re.escape(kw) + r"\b", text) or kw in text:
                return "Income"
        # If no expense category strongly matches or if it's income, default to Income
        return "Income"

    # For expenses, prioritize expense categories
    for category, keywords in active_rules.items():
        if category == "Income":
            continue
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text) or kw in text:
                return category

    # Check for income keywords if amount was unspecified but text says salary/bonus
    if amount is None:
        for kw in active_rules.get("Income", []):
            if re.search(r"\b" + re.escape(kw) + r"\b", text) or kw in text:
                return "Income"

    return "Uncategorized"


def get_category_id_for_transaction(
    description: str,
    amount: Optional[float] = None,
    assigned_category: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> int:
    """
    Determine the category name (via user input or rule engine) and resolve to SQLite category_id.
    """
    if assigned_category and assigned_category.strip() and assigned_category.strip().lower() != "auto":
        cat_name = assigned_category.strip()
    else:
        cat_name = rule_based_categorize(description, amount)

    cat_id = get_category_id_by_name(cat_name, db_path)
    if cat_id is None:
        cat_id = get_category_id_by_name("Uncategorized", db_path)
    return cat_id if cat_id is not None else 1


def categorize_dataframe(
    df: pd.DataFrame,
    description_col: str = "description",
    amount_col: str = "amount"
) -> pd.DataFrame:
    """
    Apply rule-based categorization across an entire DataFrame.
    """
    df = df.copy()
    categories = []
    for _, row in df.iterrows():
        desc = str(row.get(description_col, ""))
        amt = float(row.get(amount_col, 0.0))
        cat = rule_based_categorize(desc, amt)
        categories.append(cat)
    df["category"] = categories
    return df


# Optional Scikit-learn Classifier Scaffolding
_ml_pipeline = None

def train_optional_ml_model(transactions_df: pd.DataFrame) -> bool:
    """
    Train an optional Naive Bayes classifier if sufficient labeled historical data exists.
    """
    global _ml_pipeline
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import Pipeline

        valid_df = transactions_df.dropna(subset=["description", "category"])
        valid_df = valid_df[valid_df["category"] != "Uncategorized"]

        if len(valid_df) < 15 or valid_df["category"].nunique() < 2:
            return False

        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", MultinomialNB(alpha=0.1))
        ])
        pipeline.fit(valid_df["description"], valid_df["category"])
        _ml_pipeline = pipeline
        return True
    except Exception:
        return False


def predict_category_hybrid(
    description: str,
    amount: Optional[float] = None,
    use_ml: bool = False
) -> str:
    """
    Hybrid predictor: checks rules first; falls back to ML if uncertain; defaults to Uncategorized.
    """
    rule_cat = rule_based_categorize(description, amount)
    if rule_cat != "Uncategorized":
        return rule_cat

    global _ml_pipeline
    if use_ml and _ml_pipeline is not None and description:
        try:
            pred = _ml_pipeline.predict([description])[0]
            if amount is not None and amount > 0 and pred != "Income":
                return "Income"
            return pred
        except Exception:
            pass

    return "Uncategorized"
