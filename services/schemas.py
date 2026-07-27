from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from services.models import UserRole, VehicleStatus, RiskLevel, InstallmentStatus


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole = UserRole.SALES


class VehicleCreate(BaseModel):
    vin: str
    brand: str
    model: str
    year: int
    purchase_price: float
    selling_price: float
    mileage: int = 0


class VehicleResponse(VehicleCreate):
    id: int
    status: VehicleStatus
    model_config = ConfigDict(from_attributes=True)


class SaleCreate(BaseModel):
    vehicle_id: int
    customer_id: int
    down_payment: float
    months: int
    customer_income: float
    credit_score: int
    past_delays: int


class TaxReportResponse(BaseModel):
    gross_income: float
    total_expenses: float
    net_profit: float
    vat_liability: float
    corporate_tax_liability: float
    total_tax_due: float


class ExecutiveHealthResponse(BaseModel):
    ai_health_score: float
    financial_status: str
    profit_margin_pct: float