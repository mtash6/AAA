from sqlalchemy.orm import Session
from services.models import Transaction, Vehicle, VehicleStatus
from typing import Dict, Any


class ExecutiveAnalyticsEngine:
    @staticmethod
    def compute_business_health_score(db: Session) -> Dict[str, Any]:
        incomes = sum(t.amount for t in db.query(Transaction).filter(Transaction.type == "INCOME").all())
        expenses = sum(t.amount for t in db.query(Transaction).filter(Transaction.type == "EXPENSE").all())
        profit = incomes - expenses

        margin = (profit / incomes * 100.0) if incomes > 0 else 0.0
        health_score = min(100.0, max(0.0, 50.0 + (margin * 0.5)))

        return {
            "ai_health_score": round(health_score, 1),
            "financial_status": "STRONG" if health_score >= 70 else "STABLE" if health_score >= 50 else "CRITICAL",
            "profit_margin_pct": round(margin, 2)
        }