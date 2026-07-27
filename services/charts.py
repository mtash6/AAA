"""
Multi-Chart Visualization Engine
Supports individual plot generation and complete multi-chart dashboard suites.
"""

import io
import os
import base64
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional
from services.csv_utils import safe_read_csv, sanitize_numeric_column, map_column
from services.exceptions import TEAMAIException


class ChartEngine:

    @staticmethod
    def generate_chart_from_csv(
        file_bytes: bytes,
        x_col: str = "string",
        y_col: str = "string",
        chart_type: str = "bar",
        title: Optional[str] = None,
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates a single customized chart from uploaded CSV bytes."""
        try:
            df = safe_read_csv(file_bytes)
            
            x_col = map_column(df, [x_col, "month", "date", "category", "brand", "item", "name"])
            y_col = map_column(df, [y_col, "revenue", "price", "amount", "sales", "cost", "quantity"])

            df[y_col] = sanitize_numeric_column(df[y_col])

            fig, ax = plt.subplots(figsize=(9, 4.5))

            if chart_type.lower() == "line":
                ax.plot(df[x_col].astype(str), df[y_col], marker='o', color='#2980b9', linewidth=2.5)
            elif chart_type.lower() == "pie":
                ax.pie(df[y_col], labels=df[x_col].astype(str), autopct='%1.1f%%', startangle=140)
            elif chart_type.lower() == "scatter":
                ax.scatter(df[x_col].astype(str), df[y_col], color='#e74c3c', s=60)
            elif chart_type.lower() == "box":
                ax.boxplot(df[y_col].dropna(), patch_artist=True, boxprops=dict(facecolor='#9b59b6', color='#8e44ad'))
            else: # bar
                ax.bar(df[x_col].astype(str), df[y_col], color='#2ecc71', width=0.55)

            if chart_type.lower() != "pie":
                ax.set_xlabel(x_col.capitalize(), fontweight='bold')
                ax.set_ylabel(y_col.capitalize(), fontweight='bold')
                plt.xticks(rotation=45, ha='right')
                plt.grid(True, linestyle='--', alpha=0.5)

            ax.set_title(title or f"{chart_type.upper()}: {y_col.capitalize()} vs {x_col.capitalize()}", fontsize=12, fontweight='bold')
            plt.tight_layout()

            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                plt.savefig(save_path, dpi=150)

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150)
            plt.close(fig)
            buf.seek(0)

            return {
                "status": "SUCCESS",
                "x_axis_used": x_col,
                "y_axis_used": y_col,
                "rows_processed": len(df),
                "image_data": base64.b64encode(buf.read()).decode('utf-8')
            }
        except Exception as e:
            plt.close('all')
            raise TEAMAIException(f"Chart engine error: {str(e)}")

    @staticmethod
    def generate_multi_chart_dashboard(file_bytes: bytes, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates an Executive Dashboard Suite containing 4 distinct charts in a 2x2 grid:
        1. Bar Chart: Revenue / Main Metric
        2. Line Chart: Trend Analysis
        3. Pie Chart: Proportional Breakdown
        4. Box Plot: Anomaly / Outlier Distribution
        """
        try:
            df = safe_read_csv(file_bytes)
            
            x_col = map_column(df, ["category", "brand", "month", "item", "name", "date"])
            y_col = map_column(df, ["revenue", "amount", "price", "sales", "cost", "quantity"])

            df[y_col] = sanitize_numeric_column(df[y_col])

            fig, axs = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(f"Executive Analytics Dashboard Suite ({y_col.upper()})", fontsize=16, fontweight='bold')

            # 1. Bar Chart
            axs[0, 0].bar(df[x_col].astype(str)[:10], df[y_col][:10], color='#3498db')
            axs[0, 0].set_title("1. Metric Breakdown (Top 10)")
            axs[0, 0].tick_params(axis='x', rotation=45)
            axs[0, 0].grid(True, linestyle='--', alpha=0.3)

            # 2. Line Chart
            axs[0, 1].plot(df[x_col].astype(str), df[y_col], marker='s', color='#e67e22', linewidth=2)
            axs[0, 1].set_title("2. Trend Sequence")
            axs[0, 1].tick_params(axis='x', rotation=45)
            axs[0, 1].grid(True, linestyle='--', alpha=0.3)

            # 3. Pie Chart
            top_df = df.head(5)
            axs[1, 0].pie(top_df[y_col], labels=top_df[x_col].astype(str), autopct='%1.1f%%', startangle=90)
            axs[1, 0].set_title("3. Top 5 Contribution Share")

            # 4. Box Plot
            axs[1, 1].boxplot(df[y_col], patch_artist=True, boxprops=dict(facecolor='#2ecc71'))
            axs[1, 1].set_title("4. Distribution & Outlier Detection")
            axs[1, 1].grid(True, linestyle='--', alpha=0.3)

            plt.tight_layout(rect=[0, 0.03, 1, 0.95])

            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                plt.savefig(save_path, dpi=150)

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150)
            plt.close(fig)
            buf.seek(0)

            return {
                "status": "SUCCESS",
                "charts_generated": 4,
                "x_col": x_col,
                "y_col": y_col,
                "total_rows": len(df),
                "image_data": base64.b64encode(buf.read()).decode('utf-8')
            }
        except Exception as e:
            plt.close('all')
            raise TEAMAIException(f"Multi-chart generation failed: {str(e)}")