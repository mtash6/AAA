import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List

# إعداد نظام السجلات (Logger) لتتبع سير العمليات في بيئة الإنتاج
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """
    Quantitative Data Analytics & Machine Learning Engine.
    Implements: Anomaly Detection (IQR), Trend Forecasting (Linear Regression), 
    and ABC Inventory Classification (Pareto Principle).
    """

    # ثوابت الكلاس (Configuration Constants) لسهولة التعديل المركزي
    IQR_MULTIPLIER = 1.5
    ABC_THRESHOLDS = {"A": 70.0, "B": 90.0}

    @staticmethod
    def detect_anomalies_iqr(df: pd.DataFrame, numeric_col: str) -> Dict[str, Any]:
        """
        Detects statistical anomalies/outliers using the Interquartile Range algorithm.
        """
        # 1. التحقق من صحة المدخلات
        if numeric_col not in df.columns:
            raise KeyError(f"Column '{numeric_col}' not found in the DataFrame.")

        data = df[numeric_col].dropna()
        if len(data) < 4:
            logger.warning(f"Not enough data points in '{numeric_col}' to calculate IQR reliably.")
            return {"anomalies_found": 0, "outliers": []}

        # 2. الحسابات الإحصائية
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1

        lower_bound = q1 - (AnalyticsEngine.IQR_MULTIPLIER * iqr)
        upper_bound = q3 + (AnalyticsEngine.IQR_MULTIPLIER * iqr)

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
        Calculates linear regression trend coefficients to project future metric values.
        """
        # 1. التحقق من المدخلات
        if not values or len(values) < 2:
            raise ValueError("At least 2 historical data points are required for forecasting.")

        x = np.arange(len(values))
        y = np.array(values)

        try:
            # 2. حساب الانحدار الخطي باستخدام مكتبة NumPy لضمان أعلى دقة أداء
            m, c = np.polyfit(x, y, 1)
        except np.linalg.LinAlgError as e:
            logger.error(f"Linear Algebra error during forecasting: {str(e)}")
            raise

        # 3. بناء التنبؤات المستقبلية
        future_x = np.arange(len(values), len(values) + periods_ahead)
        forecast_values = [round(float(m * fx + c), 2) for fx in future_x]

        # هامش مرونة صغير (0.001) لتحديد الاتجاه العرضي (FLAT) بدقة
        trend_direction = "UPWARD" if m > 0.001 else "DOWNWARD" if m < -0.001 else "FLAT"

        return {
            "slope": round(float(m), 4),
            "intercept": round(float(c), 2),
            "trend_direction": trend_direction,
            "historical_last": round(float(values[-1]), 2),
            "forecast_next_periods": forecast_values
        }

    @staticmethod
    def classify_abc_inventory(
        df: pd.DataFrame, 
        cost_col: str, 
        qty_col: str, 
        item_name_col: str
    ) -> List[Dict[str, Any]]:
        """
        Executes Pareto Principle ABC Analysis efficiently using Vectorization.
        """
        # 1. التحقق من وجود جميع الأعمدة
        required_cols = [cost_col, qty_col, item_name_col]
        if not all(col in df.columns for col in required_cols):
            raise KeyError(f"DataFrame must contain all required columns: {required_cols}")

        df = df.copy()
        df["total_value"] = df[cost_col] * df[qty_col]
        df = df.sort_values(by="total_value", ascending=False).reset_index(drop=True)

        total_inventory_val = df["total_value"].sum()
        
        # 2. معالجة حالة المخزون ذو القيمة الصفرية
        if total_inventory_val == 0:
            logger.warning("Total inventory value is 0. Assigning all items to Class C.")
            df["abc_class"] = "C"
            return df[[item_name_col, "total_value", "abc_class"]].to_dict(orient="records")

        # 3. الحسابات التراكمية
        df["cum_value"] = df["total_value"].cumsum()
        df["cum_pct"] = (df["cum_value"] / total_inventory_val) * 100

        # 4. التعيين المُتجه (Vectorized Assignment) - أسرع من .apply() بشكل كبير
        conditions = [
            df["cum_pct"] <= AnalyticsEngine.ABC_THRESHOLDS["A"],
            df["cum_pct"] <= AnalyticsEngine.ABC_THRESHOLDS["B"]
        ]
        choices = ["A", "B"]
        
        # تعيين القيم بناءً على الشروط دفعة واحدة للمصفوفة بأكملها
        df["abc_class"] = np.select(conditions, choices, default="C")

        return df[[
            item_name_col, cost_col, qty_col, "total_value", "cum_pct", "abc_class"
        ]].to_dict(orient="records")
