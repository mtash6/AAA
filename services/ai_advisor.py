from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

# Import your existing models
from services.models import Budget, Transaction, Vehicle, VehicleStatus


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AdvisoryModule(str, Enum):
    FINANCE = "FINANCE"
    INVENTORY = "INVENTORY"
    CASH_FLOW = "CASH_FLOW"
    EXECUTIVE = "EXECUTIVE"


class BusinessRecommendation(BaseModel):
    module: AdvisoryModule
    priority: PriorityLevel
    title: str
    action: str
    impact_score: float = Field(..., ge=1.0, le=10.0, description="Financial urgency score from 1-10")
    metrics: Dict[str, Any] = Field(default_factory=dict)


class AIBusinessAdvisor:
    """
    Algorithmic Business Advisory Engine for Car Dealership ERP.
    Evaluates real-time financial balances, inventory aging, budget variance,
    and cash liquidity to produce actionable executive recommendations.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Run all analytical engines and return prioritized business advisories."""
        recommendations: List[BusinessRecommendation] = []

        # Run domain analytical modules
        recommendations.extend(self._analyze_budget_variances())
        recommendations.extend(self._analyze_inventory_velocity())
        recommendations.extend(self._analyze_cash_flow_liquidity())
        recommendations.extend(self._analyze_aging_inventory())

        # Fallback advisory if operations are nominal
        if not recommendations:
            recommendations.append(
                BusinessRecommendation(
                    module=AdvisoryModule.EXECUTIVE,
                    priority=PriorityLevel.LOW,
                    title="Nominal Operations",
                    action="All operational metrics are within standard tolerances. Proceed with current business plan.",
                    impact_score=1.0,
                    metrics={"status": "healthy"}
                )
            )

        # Sort by Priority level and Impact Score descending
        priority_weights = {
            PriorityLevel.CRITICAL: 4,
            PriorityLevel.HIGH: 3,
            PriorityLevel.MEDIUM: 2,
            PriorityLevel.LOW: 1,
        }
        recommendations.sort(
            key=lambda rec: (priority_weights[rec.priority], rec.impact_score),
            reverse=True,
        )

        return [rec.model_dump() for rec in recommendations]

    # --------------------------------------------------------------------------
    # Private Domain Analyzers
    # --------------------------------------------------------------------------

    def _analyze_budget_variances(self) -> List[BusinessRecommendation]:
        """Compares actual expenses against allocated budgets per category in DB."""
        recommendations = []

        # DB-side aggregate: Expense totals grouped by category
        actual_spend = (
            self.db.query(
                Transaction.category,
                func.sum(Transaction.amount).label("total_actual")
            )
            .filter(Transaction.type == "EXPENSE")
            .group_by(Transaction.category)
            .all()
        )

        if not actual_spend:
            return recommendations

        # Query dynamic budget allocations
        budgets = {b.category: b.allocated_amount for b in self.db.query(Budget).all()}

        for category, actual in actual_spend:
            actual = float(actual or 0.0)
            budgeted = float(budgets.get(category, 0.0))

            # Trigger alert if budget exists and spend exceeds budget by > 15%, or static marketing threshold
            if budgeted > 0 and actual > (budgeted * 1.15):
                variance_pct = ((actual - budgeted) / budgeted) * 100
                recommendations.append(
                    BusinessRecommendation(
                        module=AdvisoryModule.FINANCE,
                        priority=PriorityLevel.HIGH,
                        title=f"Budget Overrun: {category}",
                        action=f"Reduce {category} expenditure by {variance_pct:.1f}%. Current spend (${actual:,.2f}) exceeds target budget (${budgeted:,.2f}).",
                        impact_score=7.5,
                        metrics={"category": category, "actual": actual, "budgeted": budgeted, "variance_pct": round(variance_pct, 2)}
                    )
                )

        return recommendations

    def _analyze_inventory_velocity(self) -> List[BusinessRecommendation]:
        """Analyzes active inventory mix and alerts on low-stock high-turnover segments."""
        recommendations = []

        # Count available SUVs directly in database using SQL ILIKE pattern
        suv_count = (
            self.db.query(func.count(Vehicle.id))
            .filter(
                Vehicle.status == VehicleStatus.AVAILABLE,
                or_(
                    Vehicle.model.ilike("%SUV%"),
                    Vehicle.model.ilike("%Explorer%"),
                    Vehicle.model.ilike("%Crossover%")
                )
            )
            .scalar() or 0
        )

        min_suv_threshold = 3
        if suv_count < min_suv_threshold:
            recommendations.append(
                BusinessRecommendation(
                    module=AdvisoryModule.INVENTORY,
                    priority=PriorityLevel.MEDIUM,
                    title="Low SUV/Crossover Stock",
                    action=f"Acquire {min_suv_threshold - suv_count} additional SUV/Crossover units. Current stock ({suv_count}) is below optimal turnover requirements.",
                    impact_score=5.0,
                    metrics={"current_suv_count": suv_count, "target_minimum": min_suv_threshold}
                )
            )

        return recommendations

    def _analyze_cash_flow_liquidity(self) -> List[BusinessRecommendation]:
        """Evaluates revenue vs expense ratio using SQL aggregate functions."""
        recommendations = []

        # Total income & expenses calculated entirely on DB
        financials = (
            self.db.query(
                func.sum(case((Transaction.type == "INCOME", Transaction.amount), else_=0.0)).label("total_income"),
                func.sum(case((Transaction.type == "EXPENSE", Transaction.amount), else_=0.0)).label("total_expense")
            )
            .first()
        )

        total_income = float(financials.total_income or 0.0)
        total_expense = float(financials.total_expense or 0.0)

        if total_income > 0:
            expense_ratio = total_expense / total_income
            if expense_ratio > 0.85:
                recommendations.append(
                    BusinessRecommendation(
                        module=AdvisoryModule.CASH_FLOW,
                        priority=PriorityLevel.CRITICAL,
                        title="Critical Liquidity Alert",
                        action=f"Operating costs are consuming {expense_ratio * 100:.1f}% of total revenue. Halt non-essential capital purchases immediately.",
                        impact_score=9.5,
                        metrics={"total_income": total_income, "total_expense": total_expense, "expense_ratio": round(expense_ratio, 4)}
                    )
                )

        return recommendations

    def _analyze_aging_inventory(self) -> List[BusinessRecommendation]:
        """Detects inventory sitting on the lot longer than 60 days (holding costs)."""
        recommendations = []
        sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)

        # Check if Vehicle model has date field (e.g., date_acquired or created_at)
        if hasattr(Vehicle, "created_at"):
            aged_units_count = (
                self.db.query(func.count(Vehicle.id))
                .filter(
                    Vehicle.status == VehicleStatus.AVAILABLE,
                    Vehicle.created_at <= sixty_days_ago
                )
                .scalar() or 0
            )

            if aged_units_count > 0:
                recommendations.append(
                    BusinessRecommendation(
                        module=AdvisoryModule.INVENTORY,
                        priority=PriorityLevel.HIGH,
                        title="Aging Inventory Holding Cost",
                        action=f"Apply price markdown or promotional financing to {aged_units_count} vehicle(s) sitting in stock over 60 days.",
                        impact_score=8.0,
                        metrics={"aged_units": aged_units_count}
                    )
                )

        return recommendations
