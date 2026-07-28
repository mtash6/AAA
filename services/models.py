"""
AAA ADVANCE AMERICAN AGENCY — Enterprise Automotive ERP & Financial Database Schema
Built with SQLAlchemy 2.0 Mapped Types, Precision Numeric Types, DB Constraints, and Auto-Migration Tools.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    String,
    Numeric,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Enum as SQLEnum,
    Integer,
    Text,
    CheckConstraint,
    Index,
    func,
    inspect,
    text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from services.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    SALES = "SALES"
    HR = "HR"
    FINANCE = "FINANCE"
    INVENTORY = "INVENTORY"
    RECEPTION = "RECEPTION"
    AUDITOR = "AUDITOR"


class VehicleStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"


class InstallmentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class WorkOrderStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_PARTS = "WAITING_FOR_PARTS"
    COMPLETED = "COMPLETED"
    INVOICED = "INVOICED"


# ============================================================================
# AUTH & USER MANAGEMENT
# ============================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False), default=UserRole.SALES, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ============================================================================
# INVENTORY & SPARE PARTS
# ============================================================================

class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("purchase_price >= 0", name="ck_vehicles_purchase_price_positive"),
        CheckConstraint("selling_price >= 0", name="ck_vehicles_selling_price_positive"),
        CheckConstraint("mileage >= 0", name="ck_vehicles_mileage_positive"),
        Index("ix_vehicles_brand_model", "brand", "model"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vin: Mapped[str] = mapped_column(String(17), unique=True, index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(
        SQLEnum(VehicleStatus, native_enum=False), default=VehicleStatus.AVAILABLE, nullable=False, index=True
    )
    mileage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    sales_record: Mapped[Optional["CarSale"]] = relationship("CarSale", back_populates="vehicle", uselist=False)
    work_orders: Mapped[List["WorkOrder"]] = relationship("WorkOrder", back_populates="vehicle")


class SparePart(Base):
    __tablename__ = "spare_parts"
    __table_args__ = (
        CheckConstraint("unit_cost >= 0", name="ck_spare_parts_unit_cost_positive"),
        CheckConstraint("selling_price >= 0", name="ck_spare_parts_selling_price_positive"),
        CheckConstraint("stock_quantity >= 0", name="ck_spare_parts_stock_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    part_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False
    )


# ============================================================================
# CRM & HR
# ============================================================================

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("credit_score >= 300 AND credit_score <= 850", name="ck_customers_credit_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    national_id: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    credit_score: Mapped[int] = mapped_column(Integer, default=650, nullable=False)
    segment: Mapped[str] = mapped_column(String(30), default="REGULAR", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False
    )

    sales: Mapped[List["CarSale"]] = relationship("CarSale", back_populates="customer")
    work_orders: Mapped[List["WorkOrder"]] = relationship("WorkOrder", back_populates="customer")


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint("base_salary >= 0", name="ck_employees_base_salary_positive"),
        CheckConstraint("performance_rating >= 0.0 AND performance_rating <= 5.0", name="ck_employees_rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    department: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    performance_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=3.5, nullable=False)

    assigned_work_orders: Mapped[List["WorkOrder"]] = relationship("WorkOrder", back_populates="technician")


# ============================================================================
# SALES & INSTALLMENT MANAGEMENT
# ============================================================================

class CarSale(Base):
    __tablename__ = "car_sales"
    __table_args__ = (
        CheckConstraint("total_price >= 0", name="ck_car_sales_total_price_positive"),
        CheckConstraint("down_payment >= 0", name="ck_car_sales_down_payment_positive"),
        Index("ix_car_sales_customer_date", "customer_id", "sale_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    total_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    down_payment: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_installment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sale_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False, index=True
    )

    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="sales_record")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="sales")
    installment_plan: Mapped[Optional["InstallmentPlan"]] = relationship("InstallmentPlan", back_populates="sale", uselist=False, cascade="all, delete-orphan")


class InstallmentPlan(Base):
    __tablename__ = "installment_plans"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_inst_plan_total_amount_positive"),
        CheckConstraint("remaining_balance >= 0", name="ck_inst_plan_remaining_balance_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("car_sales.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    months: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_payment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    risk_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.0, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(SQLEnum(RiskLevel, native_enum=False), default=RiskLevel.LOW, nullable=False)

    sale: Mapped["CarSale"] = relationship("CarSale", back_populates="installment_plan")
    payments: Mapped[List["InstallmentPayment"]] = relationship("InstallmentPayment", back_populates="plan", cascade="all, delete-orphan")


class InstallmentPayment(Base):
    __tablename__ = "installment_payments"
    __table_args__ = (
        CheckConstraint("amount_due >= 0", name="ck_inst_payment_amount_due_positive"),
        CheckConstraint("amount_paid >= 0", name="ck_inst_payment_amount_paid_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("installment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False, index=True)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[InstallmentStatus] = mapped_column(SQLEnum(InstallmentStatus, native_enum=False), default=InstallmentStatus.PENDING, nullable=False, index=True)

    plan: Mapped["InstallmentPlan"] = relationship("InstallmentPlan", back_populates="payments")


# ============================================================================
# GENERAL LEDGER & DOUBLE-ENTRY ACCOUNTING
# ============================================================================

class Account(Base):
    __tablename__ = "chart_of_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(SQLEnum(AccountType, native_enum=False), nullable=False, index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)

    journal_items: Mapped[List["JournalItem"]] = relationship("JournalItem", back_populates="account")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entry_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False, index=True
    )

    items: Mapped[List["JournalItem"]] = relationship("JournalItem", back_populates="entry", cascade="all, delete-orphan")


class JournalItem(Base):
    __tablename__ = "journal_items"
    __table_args__ = (
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_journal_items_debit_credit_positive"),
        CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_journal_items_debit_xor_credit"),
        Index("ix_journal_items_entry_account", "entry_id", "account_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)

    entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="items")
    account: Mapped["Account"] = relationship("Account", back_populates="journal_items")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_transactions_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False, index=True
    )


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("monthly_limit >= 0", name="ck_budgets_limit_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)


# ============================================================================
# SERVICE CENTER & WORK ORDERS
# ============================================================================

class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint("labor_cost >= 0", name="ck_work_orders_labor_cost_positive"),
        CheckConstraint("parts_cost >= 0", name="ck_work_orders_parts_cost_positive"),
        CheckConstraint("total_cost >= 0", name="ck_work_orders_total_cost_positive"),
        Index("ix_work_orders_vehicle_status", "vehicle_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[WorkOrderStatus] = mapped_column(
        SQLEnum(WorkOrderStatus, native_enum=False), default=WorkOrderStatus.PENDING, nullable=False, index=True
    )
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    parts_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False, index=True
    )

    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="work_orders")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="work_orders")
    technician: Mapped[Optional["Employee"]] = relationship("Employee", back_populates="assigned_work_orders")


# ============================================================================
# AUDIT TRAIL
# ============================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now(), nullable=False, index=True
    )


# ============================================================================
# SCHEMA MIGRATION / SYNC UTILITY
# ============================================================================

def sync_database_schema(engine) -> None:
    """
    Self-healing migration helper.
    Ensures that existing SQLite tables automatically gain any missing columns
    (e.g., vehicle_id in work_orders, sale_date in car_sales) without dropping data.
    """
    inspector = inspect(engine)
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        # Patch 'work_orders' table if vehicle_id is missing
        if inspector.has_table("work_orders"):
            cols = [c["name"] for c in inspector.get_columns("work_orders")]
            if "vehicle_id" not in cols:
                conn.execute(text(
                    "ALTER TABLE work_orders ADD COLUMN vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE RESTRICT"
                ))

        # Patch 'car_sales' table if sale_date is missing
        if inspector.has_table("car_sales"):
            cols = [c["name"] for c in inspector.get_columns("car_sales")]
            if "sale_date" not in cols:
                conn.execute(text(
                    "ALTER TABLE car_sales ADD COLUMN sale_date DATETIME DEFAULT CURRENT_TIMESTAMP"
                ))
