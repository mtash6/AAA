"""
AAA ADVANCE AMERICAN AGENCY — Enterprise Web API (FastAPI)
API Request & Response Pydantic Schemas
Strict data validation, sanitization, and OpenAPI metadata for the Enterprise Management System.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from services.models import InstallmentStatus, RiskLevel, UserRole, VehicleStatus, AccountType


# ============================================================================
# AUTHENTICATION & USER SCHEMAS
# ============================================================================

class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token string")
    token_type: str = Field("bearer", description="Token authorization type")


class UserLogin(BaseModel):
    username: str = Field(..., description="Username or primary email")
    password: str = Field(..., description="User password")


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique username containing alphanumeric characters, underscores, or hyphens"
    )
    email: EmailStr = Field(..., description="Valid primary email address")
    password: str = Field(..., min_length=8, max_length=128, description="Raw user password")
    role: UserRole = Field(default=UserRole.SALES, description="Assigned application authorization role")


class UserResponse(BaseModel):
    id: int = Field(..., gt=0, description="User database primary key")
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ============================================================================
# VEHICLE SCHEMAS
# ============================================================================

class VehicleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    vin: str = Field(..., min_length=17, max_length=17, description="Standard 17-character Vehicle Identification Number")
    brand: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1900, description="Manufacturing model year")
    purchase_price: float = Field(..., gt=0.0, description="Acquisition cost in USD")
    selling_price: float = Field(..., gt=0.0, description="Target listing price in USD")
    mileage: int = Field(default=0, ge=0, description="Odometer reading")

    @field_validator("vin")
    @classmethod
    def normalize_vin(cls, v: str) -> str:
        """Ensures VIN is always uppercase and trimmed."""
        return v.strip().upper()

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Dynamically validates model year against current calendar year + 1."""
        max_year = datetime.now().year + 1
        if v > max_year:
            raise ValueError(f"Vehicle model year cannot exceed {max_year}")
        return v

    @field_validator("selling_price")
    @classmethod
    def validate_pricing(cls, v: float, info) -> float:
        """Ensures target selling price is not lower than purchase price."""
        purchase_price = info.data.get("purchase_price")
        if purchase_price is not None and v < purchase_price:
            raise ValueError("Selling price cannot be lower than purchase price.")
        return v


class VehicleResponse(VehicleCreate):
    id: int = Field(..., gt=0, description="Database primary key")
    status: VehicleStatus = Field(..., description="Current vehicle inventory status")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ============================================================================
# CUSTOMER SCHEMAS
# ============================================================================

class CustomerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(..., min_length=2, max_length=100)
    national_id: str = Field(..., min_length=5, max_length=30)
    phone: str = Field(..., min_length=7, max_length=20)
    email: EmailStr = Field(...)
    credit_score: int = Field(default=650, ge=300, le=850)
    segment: str = Field(default="STANDARD", max_length=30)


class CustomerResponse(CustomerCreate):
    id: int = Field(..., gt=0)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SPARE PARTS SCHEMAS
# ============================================================================

class SparePartCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    part_number: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    unit_cost: float = Field(..., gt=0.0)
    selling_price: float = Field(..., gt=0.0)
    stock_quantity: int = Field(default=0, ge=0)


class SparePartResponse(SparePartCreate):
    id: int = Field(..., gt=0)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SALES & FINANCING SCHEMAS
# ============================================================================

class SaleCreate(BaseModel):
    vehicle_id: int = Field(..., gt=0, description="Target vehicle ID")
    customer_id: int = Field(..., gt=0, description="Purchasing customer ID")
    down_payment: float = Field(..., ge=0.0, description="Initial payment made by customer")
    months: int = Field(default=0, ge=0, le=120, description="Financing term in months (0 for cash purchase, 1-120 for installments)")
    customer_income: float = Field(..., gt=0.0, description="Monthly declared income")
    credit_score: int = Field(..., ge=300, le=850, description="FICO/Credit bureau score (300-850)")
    past_delays: int = Field(default=0, ge=0, description="Historical payment delay occurrences")


class InstallmentPlanResponse(BaseModel):
    id: int = Field(..., gt=0)
    sale_id: int
    total_amount: float
    remaining_balance: float
    months: int
    monthly_payment: float
    risk_score: float
    risk_level: RiskLevel
    status: InstallmentStatus

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    id: int = Field(..., gt=0)
    vehicle_id: int
    customer_id: int
    total_price: float
    down_payment: float
    is_installment: bool
    sale_date: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# GENERAL LEDGER & ACCOUNTING SCHEMAS
# ============================================================================

class AccountResponse(BaseModel):
    id: int = Field(..., gt=0)
    code: str
    name: str
    account_type: AccountType
    balance: float

    model_config = ConfigDict(from_attributes=True)


class TaxReportResponse(BaseModel):
    gross_income: float = Field(..., ge=0.0)
    total_expenses: float = Field(..., ge=0.0)
    net_profit: float = Field(...)
    vat_liability: float = Field(..., ge=0.0)
    corporate_tax_liability: float = Field(..., ge=0.0)
    total_tax_due: float = Field(..., ge=0.0)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EXECUTIVE & AI ANALYTICS SCHEMAS
# ============================================================================

class ExecutiveHealthResponse(BaseModel):
    ai_health_score: float = Field(..., ge=0.0, le=100.0, description="Composite health index (0-100)")
    financial_status: str = Field(..., description="Qualitative status descriptor (e.g., EXCELLENT, STABLE, ATTENTION_REQUIRED)")
    profit_margin_pct: float = Field(..., description="Calculated profit margin percentage")

    model_config = ConfigDict(from_attributes=True)


class AIRecommendation(BaseModel):
    id: str
    title: str
    module: str
    priority: str
    impact_score: float
    action: str


# ============================================================================
# CSV INGESTION SCHEMAS
# ============================================================================

class CSVAnomalyDetails(BaseModel):
    method: str
    upper_bound_threshold: float
    outliers_detected: int


class CSVIngestResponse(BaseModel):
    status: str
    filename: str
    rows_processed: int
    target: str
    anomaly_detection: CSVAnomalyDetails
