"""
Robust CSV Ingestion & Sanitization Helper Services
Handles byte decodes, multi-encoding & multi-delimiter fallbacks,
whitespace stripping, accounting/currency parsing, and fuzzy column mapping.
"""

import io
import re
import difflib
import pandas as pd
import numpy as np
from typing import List, Optional, Union

# Fallback exception handler if TEAMAIException isn't available
try:
    from services.exceptions import TEAMAIException
except ImportError:
    class TEAMAIException(Exception):
        pass


def safe_read_csv(
    file_bytes: bytes,
    strip_cell_whitespace: bool = True
) -> pd.DataFrame:
    """
    Attempts to read CSV bytes across multiple encodings and delimiters 
    to prevent upload crashes on non-standard files.
    """
    if not file_bytes or len(file_bytes.strip()) == 0:
        raise TEAMAIException("Uploaded file is empty.")

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "iso-8859-1"]
    delimiters = [",", ";", "\t", "|"]
    df: Optional[pd.DataFrame] = None

    for enc in encodings:
        for sep in delimiters:
            try:
                candidate_df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=enc,
                    sep=sep,
                    engine="python",
                    on_bad_lines="skip"
                )
                # Accept if it successfully parsed multiple columns or if using standard comma
                if candidate_df.shape[1] > 1 or sep == ",":
                    df = candidate_df
                    break
            except Exception:
                continue
        if df is not None:
            break

    if df is None:
        raise TEAMAIException(
            "Unable to parse CSV file. Please verify file format and encoding (UTF-8 recommended)."
        )

    if df.empty:
        raise TEAMAIException("The uploaded CSV contains no data rows.")

    # Clean column headers (strip whitespace, quotes, and residual UTF-8 BOMs)
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace('"', '', regex=False)
        .str.replace("'", '', regex=False)
        .str.replace("\ufeff", "", regex=False)
    )

    # Strip leading/trailing whitespace from object/string cells
    if strip_cell_whitespace:
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            df[col] = df[col].astype(str).str.strip()

    return df


def sanitize_numeric_column(
    series: pd.Series, 
    fill_value: Optional[float] = 0.0
) -> pd.Series:
    """
    Sanitizes monetary or numeric strings containing symbols ($ € £ ¥ %),
    commas, whitespace, and accounting negative formats like '(100.00)'.
    """
    if series is None or series.empty:
        return pd.Series(dtype=float)

    s_str = series.astype(str).str.strip()

    # Convert accounting negative format: "(1,250.50)" -> "-1250.50"
    s_str = s_str.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    # Strip currency symbols, commas, spaces, percentages, keeping digits, '-', and '.'
    s_cleaned = s_str.str.replace(r"[^\d.-]", "", regex=True)

    numeric_series = pd.to_numeric(s_cleaned, errors="coerce")
    
    if fill_value is not None:
        numeric_series = numeric_series.fillna(fill_value)

    return numeric_series


def map_column(
    df: pd.DataFrame, 
    possible_names: List[str], 
    default_col: Optional[str] = None,
    raise_on_missing: bool = False
) -> str:
    """
    Fuzzy matches column names using case-insensitive, normalized symbol stripping,
    and string similarity ratios.
    """
    if df.columns.empty:
        if raise_on_missing:
            raise KeyError("DataFrame contains no columns to map.")
        return default_col or ""

    def _normalize(s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", str(s)).lower()

    df_cols_original = list(df.columns)
    normalized_cols_map = {_normalize(c): c for c in df_cols_original}

    # Tier 1: Exact and Normalized Case/Symbol-Insensitive Match
    for name in possible_names:
        norm_name = _normalize(name)
        if norm_name in normalized_cols_map:
            return normalized_cols_map[norm_name]

    # Tier 2: Fuzzy Similarity Matching (cutoff ratio 70%)
    norm_col_keys = list(normalized_cols_map.keys())
    for name in possible_names:
        norm_name = _normalize(name)
        matches = difflib.get_close_matches(norm_name, norm_col_keys, n=1, cutoff=0.7)
        if matches:
            return normalized_cols_map[matches[0]]

    # Tier 3: Default Explicit Fallback
    if default_col and default_col in df.columns:
        return default_col

    if raise_on_missing:
        raise KeyError(f"Could not map target columns {possible_names} to DataFrame headers: {df_cols_original}")

    # Fallback to first available column
    return df.columns[0]
