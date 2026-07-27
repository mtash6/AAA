import pandas as pd
from typing import List, Dict

class AIInventoryEngine:
    @staticmethod
    def analyze_stock_velocity(vehicles_data: List[Dict]) -> Dict:
        """
        Analyzes vehicle stock to classify Fast-Moving vs Slow-Moving inventory.
        """
        if not vehicles_data:
            return {"fast_moving": [], "slow_moving": [], "recommendations": []}

        df = pd.DataFrame(vehicles_data)
        
        # Aggregate by brand
        brand_summary = df.groupby('brand').agg(
            total_stock=('id', 'count'),
            sold_count=('status', lambda x: (x == 'SOLD').sum())
        ).reset_index()

        brand_summary['sell_through_rate'] = brand_summary['sold_count'] / brand_summary['total_stock']

        fast_moving = brand_summary[brand_summary['sell_through_rate'] >= 0.5]['brand'].tolist()
        slow_moving = brand_summary[brand_summary['sell_through_rate'] < 0.5]['brand'].tolist()

        recommendations = []
        for brand in fast_moving:
            recommendations.append(f"Increase inventory allocation for {brand} by 20% next month.")
        for brand in slow_moving:
            recommendations.append(f"Offer targeted promotional discounts or lower margins on {brand} stock.")

        return {
            "fast_moving_brands": fast_moving,
            "slow_moving_brands": slow_moving,
            "actionable_recommendations": recommendations
        }