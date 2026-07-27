"""
Robust CSV Ingestion & Sanitization Helper
Handles byte decodes, multi-encoding fallbacks, whitespace stripping,
currency symbol removal, and automatic column mapping.
"""

import io
import pandas as pd
from typing import List, Optional
from services.exceptions import TEAMAIException


def safe_read_csv(file_bytes: bytes) -> pd.DataFrame:
    """
    Attempts to read CSV bytes across multiple encodings to prevent upload crashes.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise TEAMAIException("Uploaded file is empty.")

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    df = None

    for enc in encodings:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
            break
        except Exception:
            continue

    if df is None:
        raise TEAMAIException("Unable to parse CSV file. Please verify file encoding (UTF-8 recommended).")

    if df.empty:
        raise TEAMAIException("The uploaded CSV contains no data rows.")

    # Clean column headers (remove spaces, quotes, and BOM characters)
    df.columns = df.columns.astype(str).str.strip().str.replace('"', '').str.replace("'", "")
    return df


def sanitize_numeric_column(series: pd.Series) -> pd.Series:
    """
    Sanitizes monetary or numeric strings containing symbols like '$' or commas ','.
    """
    cleaned = (
        series.astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce").fillna(0.0)


def map_column(df: pd.DataFrame, possible_names: List[str], default_col: Optional[str] = None) -> str:
    """
    Fuzzy matches column names regardless of case or slight naming variations.
    """
    cols_lower = {c.lower(): c for c in df.columns}
    for name in possible_names:
        if name.lower() in cols_lower:
            return cols_lower[name.lower()]

    if default_col and default_col in df.columns:
        return default_col

    # Fallback to first column if no match found
    return df.columns[0]