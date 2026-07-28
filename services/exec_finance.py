import logging
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from services.models import Transaction, Vehicle, VehicleStatus

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# DATA CONTRACTS
# --------------------------------------------------------------------------

class HealthStatus(str, Enum):
    STRONG = "STRONG"
    STABLE = "STABLE"
    CRITICAL = "CRITICAL"


class FinancialMetrics(BaseModel):
    total_income: float
    total_expense: float
    net_profit: float
    profit_margin_pct: float


class InventoryHealthMetrics(BaseModel):
    total_vehicles: int
    available_vehicles: int
    sold_vehicles: int
    sell_through_rate: float = Field(..., ge=0.0, le=1.0)


class ExecutiveHealthReport(BaseModel):
    ai_health_score: float = Field(..., ge=0.0, le=100.0)
    financial_status: HealthStatus
    financials: FinancialMetrics
    inventory: InventoryHealthMetrics
    actionable_insights: List[str]


# --------------------------------------------------------------------------
# EXECUTIVE ANALYTICS ENGINE
# --------------------------------------------------------------------------

class ExecutiveAnalyticsEngine:
    """
    Executive Business Intelligence & Operations Engine.
    Executes database-level aggregations to derive multi-factor financial
    health, inventory velocity, and operational insights.
    """

    @staticmethod
    def compute_business_health_score(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ExecutiveHealthReport:
        """
        Computes financial margins, inventory sell-through rates, and executive health metrics.
        """
        # 1. SQL-Level Aggregation for Transactions
        tx_query = db.query(
            func.coalesce(
                func.sum(case((Transaction.type == "INCOME", Transaction.amount), else_=0.0)), 0.0
            ).label("total_income"),
            func.coalesce(
                func.sum(case((Transaction.type == "EXPENSE", Transaction.amount), else_=0.0)), 0.0
            ).label("total_expense")
        )

        if start_date:
            tx_query = tx_query.filter(Transaction.timestamp >= start_date)
        if end_date:
            tx_query = tx_query.filter(Transaction.timestamp <= end_date)

        fin_result = tx_query.first()
        incomes = float(fin_result.total_income) if fin_result else 0.0
        expenses = float(fin_result.total_expense) if fin_result else 0.0
        profit = incomes - expenses
        margin = (profit / incomes * 100.0) if incomes > 0 else 0.0

        # 2. SQL-Level Aggregation for Vehicle Fleet
        veh_query = db.query(
            func.count(Vehicle.id).label("total"),
            func.coalesce(func.sum(case((Vehicle.status == VehicleStatus.SOLD, 1), else_=0)), 0).label("sold"),
            func.coalesce(func.sum(case((Vehicle.status == VehicleStatus.AVAILABLE, 1), else_=0)), 0).label("available")
        )

        veh_result = veh_query.first()
        total_vehicles = int(veh_result.total) if veh_result else 0
        sold_vehicles = int(veh_result.sold) if veh_result else 0
        available_vehicles = int(veh_result.available) if veh_result else 0

        sell_through_rate = (sold_vehicles / total_vehicles) if total_vehicles > 0 else 0.0

        # 3. Composite Health Score Algorithm
        # Weighted sub-scores: 60% Profit Margin, 40% Inventory Velocity
        margin_score = min(100.0, max(0.0, 50.0 + (margin * 1.0)))
        velocity_score = min(100.0, sell_through_rate * 100.0)

        composite_score = round(0.60 * margin_score + 0.40 * velocity_score, 1)

        # Health Classification
        if composite_score >= 70.0:
            status_label = HealthStatus.STRONG
        elif composite_score >= 50.0:
            status_label = HealthStatus.STABLE
        else:
            status_label = HealthStatus.CRITICAL

        # Dynamic Operational Insights
        insights: List[str] = []
        if margin < 15.0:
            insights.append(f"Operating margin is low ({margin:.1f}%). Audit discretionary expenses and vehicle pricing discounts.")
        if sell_through_rate < 0.40:
            insights.append(f"Inventory velocity is sluggish ({sell_through_rate * 100:.1f}% sell-through). Consider promotional clearance.")
        if not insights:
            insights.append("Operational metrics and financial margins are well within target thresholds.")

        return ExecutiveHealthReport(
            ai_health_score=composite_score,
            financial_status=status_label,
            financials=FinancialMetrics(
                total_income=round(incomes, 2),
                total_expense=round(expenses, 2),
                net_profit=round(profit, 2),
                profit_margin_pct=round(margin, 2)
            ),
            inventory=InventoryHealthMetrics(
                total_vehicles=total_vehicles,
                available_vehicles=available_vehicles,
                sold_vehicles=sold_vehicles,
                sell_through_rate=round(sell_through_rate, 4)
            ),
            actionable_insights=insights
        )
