import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# DATA CONTRACTS
# --------------------------------------------------------------------------

class BrandVelocityMetric(BaseModel):
    brand: str
    total_stock: int
    sold_count: int
    available_count: int
    sell_through_rate: float = Field(..., ge=0.0, le=1.0)
    avg_days_in_inventory: float
    capital_tied_up_usd: float
    velocity_class: str  # "FAST_MOVING" | "MODERATE" | "SLOW_MOVING" | "DEAD_STOCK"


class InventoryVelocityReport(BaseModel):
    summary: Dict[str, Any]
    brand_analytics: List[BrandVelocityMetric]
    fast_moving_brands: List[str]
    slow_moving_brands: List[str]
    capital_at_risk_usd: float
    actionable_recommendations: List[str]


# --------------------------------------------------------------------------
# INVENTORY ANALYTICS ENGINE
# --------------------------------------------------------------------------

class AIInventoryEngine:
    """
    Enterprise Supply Chain & Inventory Analytics Engine.
    Evaluates Sell-Through Rates (STR), Days Sales of Inventory (DSI),
    Capital Risk, and Strategic Reorder/Liquidation Signals.
    """

    @staticmethod
    def analyze_stock_velocity(
        vehicles_data: List[Dict[str, Any]],
        fast_moving_threshold: float = 0.5,
        aging_days_threshold: int = 60
    ) -> InventoryVelocityReport:
        """
        Analyzes inventory velocity, holding costs, and capital risk across vehicle brands.
        """
        if not vehicles_data:
            return InventoryVelocityReport(
                summary={"total_vehicles": 0, "overall_sell_through_rate": 0.0},
                brand_analytics=[],
                fast_moving_brands=[],
                slow_moving_brands=[],
                capital_at_risk_usd=0.0,
                actionable_recommendations=["No inventory data provided for analysis."]
            )

        df = pd.DataFrame(vehicles_data)

        # Defensive Column Normalization
        required_defaults = {
            'brand': 'Unknown',
            'status': 'AVAILABLE',
            'purchase_price': 0.0,
            'days_in_stock': 0
        }
        for col, default_val in required_defaults.items():
            if col not in df.columns:
                df[col] = default_val

        df['purchase_price'] = pd.to_numeric(df['purchase_price'], errors='coerce').fillna(0.0)
        df['days_in_stock'] = pd.to_numeric(df['days_in_stock'], errors='coerce').fillna(0)

        brand_metrics_list: List[BrandVelocityMetric] = []
        fast_moving: List[str] = []
        slow_moving: List[str] = []
        recommendations: List[str] = []
        total_capital_at_risk = 0.0

        # Aggregate by Brand
        for brand, group in df.groupby('brand'):
            total_stock = len(group)
            sold_count = int((group['status'] == 'SOLD').sum())
            available_count = total_stock - sold_count

            sell_through = float(sold_count / total_stock) if total_stock > 0 else 0.0
            avg_dsi = float(group['days_in_stock'].mean())

            # Monetary capital locked in unsold units
            unsold_units = group[group['status'] != 'SOLD']
            capital_tied = float(unsold_units['purchase_price'].sum())

            # Dynamic Velocity Classification
            if sell_through >= fast_moving_threshold and avg_dsi <= aging_days_threshold:
                v_class = "FAST_MOVING"
                fast_moving.append(str(brand))
            elif avg_dsi > 90:
                v_class = "DEAD_STOCK"
                slow_moving.append(str(brand))
                total_capital_at_risk += capital_tied
            elif sell_through < 0.25 or avg_dsi > aging_days_threshold:
                v_class = "SLOW_MOVING"
                slow_moving.append(str(brand))
                total_capital_at_risk += capital_tied
            else:
                v_class = "MODERATE"

            metric = BrandVelocityMetric(
                brand=str(brand),
                total_stock=total_stock,
                sold_count=sold_count,
                available_count=available_count,
                sell_through_rate=round(sell_through, 4),
                avg_days_in_inventory=round(avg_dsi, 1),
                capital_tied_up_usd=round(capital_tied, 2),
                velocity_class=v_class
            )
            brand_metrics_list.append(metric)

        # Generate Strategic Recommendations
        for b in brand_metrics_list:
            if b.velocity_class == "FAST_MOVING":
                recommendations.append(
                    f"HIGH DEMAND [{b.brand}]: Sell-through rate is {b.sell_through_rate * 100:.1f}% "
                    f"(Avg {b.avg_days_in_inventory:.0f} DSI). Increase inventory allocation by 20-25%."
                )
            elif b.velocity_class in ["SLOW_MOVING", "DEAD_STOCK"]:
                recommendations.append(
                    f"CAPITAL RISK [{b.brand}]: ${b.capital_tied_up_usd:,.2f} tied up in unsold units "
                    f"({b.velocity_class.replace('_', ' ')}). Implement targeted promotional discounts or floorplan clearance."
                )

        overall_str = float((df['status'] == 'SOLD').sum() / len(df)) if len(df) > 0 else 0.0

        return InventoryVelocityReport(
            summary={
                "total_vehicles": len(df),
                "total_brands": len(brand_metrics_list),
                "overall_sell_through_rate": round(overall_str, 4),
            },
            brand_analytics=brand_metrics_list,
            fast_moving_brands=fast_moving,
            slow_moving_brands=slow_moving,
            capital_at_risk_usd=round(total_capital_at_risk, 2),
            actionable_recommendations=recommendations or ["Inventory turnover is operating within target thresholds."]
        )
