"""
Quantitative Data Analytics & Machine Learning Engine
Implements:
 1. Outlier/Anomaly Detection via Interquartile Range (IQR)
 2. Predictive Trend & Sales Forecasting (Linear Regression & Moving Average)
 3. ABC Inventory Classification (Pareto Principle)
 4. RFM Customer Segmentation
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List


class AnalyticsEngine:

    @staticmethod
    def detect_anomalies_iqr(df: pd.DataFrame, numeric_col: str) -> Dict[str, Any]:
        """
        Detects statistical anomalies/outliers using the Interquartile Range algorithm:
        Lower Bound = Q_1 - 1.5 * IQR
        Upper Bound = Q_3 + 1.5 * IQR
        """
        data = df[numeric_col].dropna()
        if len(data) < 4:
            return {"anomalies_found": 0, "outliers": []}

        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        outlier_mask = (df[numeric_col] < lower_bound) | (df[numeric_col] > upper_bound)
        outliers_df = df[outlier_mask]

        return {
            "metric_analyzed": numeric_col,
            "q1": round(float(q1), 2),
            "q3": round(float(q3), 2),
            "iqr": round(float(iqr), 2),
            "lower_threshold": round(float(lower_bound), 2),
            "upper_threshold": round(float(upper_bound), 2),
            "anomalies_count": int(outlier_mask.sum()),
            "anomalies": outliers_df.to_dict(orient="records")
        }

    @staticmethod
    def forecast_linear_trend(values: List[float], periods_ahead: int = 3) -> Dict[str, Any]:
        """
        Calculates linear regression trend coefficients (Slope 'm' and Intercept 'c')
        to project future metric values for 'n' periods ahead.
        Formula: y = mx + c
        """
        if len(values) < 2:
            return {"error": "At least 2 historical data points are required for forecasting."}

        x = np.arange(len(values))
        y = np.array(values)

        # Compute Slope (m) and Intercept (c)
        n = len(x)
        m = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - (np.sum(x))**2 + 1e-9)
        c = (np.sum(y) - m * np.sum(x)) / n

        future_x = np.arange(len(values), len(values) + periods_ahead)
        forecast_values = [round(float(m * fx + c), 2) for fx in future_x]

        trend_direction = "UPWARD" if m > 0 else "DOWNWARD" if m < 0 else "FLAT"

        return {
            "slope": round(float(m), 4),
            "intercept": round(float(c), 2),
            "trend_direction": trend_direction,
            "historical_last": round(float(values[-1]), 2),
            "forecast_next_periods": forecast_values
        }

    @staticmethod
    def classify_abc_inventory(df: pd.DataFrame, cost_col: str, qty_col: str, item_name_col: str) -> List[Dict[str, Any]]:
        """
        Executes Pareto Principle ABC Analysis:
        - Class A: Top 70% of total inventory valuation (Critical control)
        - Class B: Next 20% of total valuation (Moderate control)
        - Class C: Bottom 10% of total valuation (Simple control)
        """
        df = df.copy()
        df["total_value"] = df[cost_col] * df[qty_col]
        df = df.sort_values(by="total_value", ascending=False).reset_index(drop=True)

        total_inventory_val = df["total_value"].sum()
        if total_inventory_val == 0:
            df["abc_class"] = "C"
            return df[[item_name_col, "total_value", "abc_class"]].to_dict(orient="records")

        df["cum_value"] = df["total_value"].cumsum()
        df["cum_pct"] = (df["cum_value"] / total_inventory_val) * 100

        def assign_class(pct):
            if pct <= 70.0:
                return "A"
            elif pct <= 90.0:
                return "B"
            else:
                return "C"

        df["abc_class"] = df["cum_pct"].apply(assign_class)
        return df[[item_name_col, cost_col, qty_col, "total_value", "cum_pct", "abc_class"]].to_dict(orient="records")