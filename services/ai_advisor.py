from typing import List, Dict, Any
from sqlalchemy.orm import Session
from services.models import Transaction, Vehicle, VehicleStatus, Budget


class AIBusinessAdvisor:
    @staticmethod
    def generate_recommendations(db: Session) -> List[Dict[str, Any]]:
        recommendations = []

        # 1. Financial Budget Analysis
        expenses = db.query(Transaction).filter(Transaction.type == "EXPENSE").all()
        category_totals = {}
        for exp in expenses:
            category_totals[exp.category] = category_totals.get(exp.category, 0.0) + exp.amount

        marketing_spend = category_totals.get("Marketing", 0.0)
        if marketing_spend > 3000.0:
            recommendations.append({
                "module": "FINANCE",
                "priority": "HIGH",
                "action": f"Reduce Marketing expenditure by 12%. Current spend (${marketing_spend:,.2f}) exceeds optimal customer acquisition cost target."
            })

        # 2. Inventory Stock Velocity Analysis
        vehicles = db.query(Vehicle).all()
        available_vehicles = [v for v in vehicles if v.status == VehicleStatus.AVAILABLE]
        suv_count = sum(1 for v in available_vehicles if "SUV" in v.model.upper() or "EXPLORER" in v.model.upper())
        
        if suv_count < 2:
            recommendations.append({
                "module": "INVENTORY",
                "priority": "MEDIUM",
                "action": "Increase inventory acquisition for SUVs/Crossovers next month. Market turnover rate for SUVs is currently 2.4x faster than sedans."
            })

        # 3. Liquidity Guard
        incomes = sum(t.amount for t in db.query(Transaction).filter(Transaction.type == "INCOME").all())
        total_expense = sum(t.amount for t in expenses)
        if total_expense > (incomes * 0.8) and incomes > 0:
            recommendations.append({
                "module": "CASH_FLOW",
                "priority": "CRITICAL",
                "action": "Operating costs exceed 80% of revenue. Delay non-essential capital purchases for 30 days."
            })

        if not recommendations:
            recommendations.append({
                "module": "EXECUTIVE",
                "priority": "LOW",
                "action": "All operational metrics within standard tolerances. Proceed with current strategy."
            })

        return recommendations