import io
import os
import base64
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
# Using Object-Oriented API for thread-safety in backend servers
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from typing import Dict, Any, Optional

# Mocking external services for the script to be valid standalone (if needed)
class TEAMAIException(Exception): pass
def safe_read_csv(file_bytes): return pd.read_csv(io.BytesIO(file_bytes))
def sanitize_numeric_column(col): return pd.to_numeric(col, errors='coerce')
def map_column(df, possible_names): 
    for name in possible_names:
        if name in df.columns: return name
    return df.columns[0] if not df.empty else "unknown"

class ChartTheme:
    """Centralized theme configuration for consistent, professional branding."""
    COLORS = {
        "primary": "#2980b9",
        "success": "#2ecc71",
        "danger": "#e74c3c",
        "warning": "#e67e22",
        "purple": "#9b59b6"
    }
    PIE_COLORS = ["#3498db", "#2ecc71", "#e74c3c", "#f1c40f", "#9b59b6", "#34495e"]
    GRID_ALPHA = 0.3

class ChartEngine:
    """
    Enterprise-grade Multi-Chart Visualization Engine.
    Utilizes Matplotlib's Object-Oriented API for thread-safety and prevents memory leaks.
    """

    @staticmethod
    def _aggregate_data(df: pd.DataFrame, x_col: str, y_col: str, top_n: Optional[int] = None) -> pd.DataFrame:
        """Aggregates categorical data to prevent rendering massive unreadable points."""
        agg_df = df.groupby(x_col, as_index=False)[y_col].sum()
        agg_df = agg_df.sort_values(by=y_col, ascending=False).reset_index(drop=True)
        if top_n:
            agg_df = agg_df.head(top_n)
        return agg_df

    @staticmethod
    def generate_chart_from_csv(
        file_bytes: bytes,
        x_col: str = "string",
        y_col: str = "string",
        chart_type: str = "bar",
        title: Optional[str] = None,
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            df = safe_read_csv(file_bytes)
            if df.empty:
                raise ValueError("Uploaded CSV data is empty.")
            
            x_col = map_column(df, [x_col, "month", "date", "category", "brand", "item", "name"])
            y_col = map_column(df, [y_col, "revenue", "price", "amount", "sales", "cost", "quantity"])
            df[y_col] = sanitize_numeric_column(df[y_col])

            # Use Object-Oriented API (Figure/Canvas) instead of stateful pyplot
            fig = Figure(figsize=(9, 4.5), dpi=150)
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)

            c_type = chart_type.lower()
            
            # Aggregate data for categorical charts to ensure readability
            if c_type in ["bar", "pie"]:
                plot_df = ChartEngine._aggregate_data(df, x_col, y_col, top_n=15 if c_type == "bar" else 5)
            else:
                plot_df = df.copy()

            if c_type == "line":
                plot_df = plot_df.sort_values(by=x_col)
                ax.plot(plot_df[x_col].astype(str), plot_df[y_col], marker='o', color=ChartTheme.COLORS["primary"], linewidth=2.5)
            elif c_type == "pie":
                ax.pie(plot_df[y_col], labels=plot_df[x_col].astype(str), autopct='%1.1f%%', startangle=140, colors=ChartTheme.PIE_COLORS)
            elif c_type == "scatter":
                ax.scatter(plot_df[x_col].astype(str), plot_df[y_col], color=ChartTheme.COLORS["danger"], s=60, alpha=0.7)
            elif c_type == "box":
                ax.boxplot(plot_df[y_col].dropna(), patch_artist=True, boxprops=dict(facecolor=ChartTheme.COLORS["purple"], color='#8e44ad'))
                ax.set_xticklabels([y_col.capitalize()])
            else:  # bar
                ax.bar(plot_df[x_col].astype(str), plot_df[y_col], color=ChartTheme.COLORS["success"], width=0.55)

            if c_type != "pie":
                ax.set_xlabel(x_col.capitalize(), fontweight='bold')
                ax.set_ylabel(y_col.capitalize(), fontweight='bold')
                ax.tick_params(axis='x', rotation=45)
                # Fix alignment for rotated labels
                for label in ax.get_xticklabels():
                    label.set_horizontalalignment('right')
                ax.grid(True, linestyle='--', alpha=ChartTheme.GRID_ALPHA)

            ax.set_title(title or f"{chart_type.upper()}: {y_col.capitalize()} by {x_col.capitalize()}", fontsize=12, fontweight='bold')
            fig.tight_layout()

            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                fig.savefig(save_path, dpi=150)

            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150)
            image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            return {
                "status": "SUCCESS",
                "x_axis_used": x_col,
                "y_axis_used": y_col,
                "rows_processed": len(df),
                "image_data": image_base64
            }
        except Exception as e:
            raise TEAMAIException(f"Chart engine error: {str(e)}")

    @staticmethod
    def generate_multi_chart_dashboard(file_bytes: bytes, save_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            df = safe_read_csv(file_bytes)
            if df.empty:
                raise ValueError("Uploaded CSV data is empty.")
            
            x_col = map_column(df, ["category", "brand", "month", "item", "name", "date"])
            y_col = map_column(df, ["revenue", "amount", "price", "sales", "cost", "quantity"])
            df[y_col] = sanitize_numeric_column(df[y_col])

            fig = Figure(figsize=(14, 10), dpi=150)
            canvas = FigureCanvas(fig)
            axs = fig.subplots(2, 2)
            fig.suptitle(f"Executive Analytics Dashboard Suite ({y_col.upper()})", fontsize=16, fontweight='bold')

            # Aggregate data for clean categorical plotting
            agg_df = ChartEngine._aggregate_data(df, x_col, y_col)

            # 1. Bar Chart (Top 10)
            top_10 = agg_df.head(10)
            axs[0, 0].bar(top_10[x_col].astype(str), top_10[y_col], color=ChartTheme.COLORS["primary"])
            axs[0, 0].set_title("1. Metric Breakdown (Top 10)")
            axs[0, 0].tick_params(axis='x', rotation=45)
            for label in axs[0, 0].get_xticklabels(): label.set_horizontalalignment('right')
            axs[0, 0].grid(True, linestyle='--', alpha=ChartTheme.GRID_ALPHA)

            # 2. Line Chart (Trend Sequence)
            trend_df = df.groupby(x_col, as_index=False)[y_col].sum().sort_values(by=x_col)
            axs[0, 1].plot(trend_df[x_col].astype(str), trend_df[y_col], marker='s', color=ChartTheme.COLORS["warning"], linewidth=2)
            axs[0, 1].set_title("2. Trend Sequence")
            axs[0, 1].tick_params(axis='x', rotation=45)
            for label in axs[0, 1].get_xticklabels(): label.set_horizontalalignment('right')
            axs[0, 1].grid(True, linestyle='--', alpha=ChartTheme.GRID_ALPHA)

            # 3. Pie Chart (Top 5 Share)
            top_5 = agg_df.head(5)
            axs[1, 0].pie(top_5[y_col], labels=top_5[x_col].astype(str), autopct='%1.1f%%', startangle=90, colors=ChartTheme.PIE_COLORS)
            axs[1, 0].set_title("3. Top 5 Contribution Share")

            # 4. Box Plot (Distribution & Outliers on RAW data)
            axs[1, 1].boxplot(df[y_col].dropna(), patch_artist=True, boxprops=dict(facecolor=ChartTheme.COLORS["success"]))
            axs[1, 1].set_title("4. Distribution & Outlier Detection")
            axs[1, 1].grid(True, linestyle='--', alpha=ChartTheme.GRID_ALPHA)
            axs[1, 1].set_xticklabels([y_col.capitalize()])

            fig.tight_layout(rect=[0, 0.03, 1, 0.95])

            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                fig.savefig(save_path, dpi=150)

            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150)
            image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            return {
                "status": "SUCCESS",
                "charts_generated": 4,
                "x_col": x_col,
                "y_col": y_col,
                "total_rows": len(df),
                "image_data": image_base64
            }
        except Exception as e:
            raise TEAMAIException(f"Multi-chart generation failed: {str(e)}")
