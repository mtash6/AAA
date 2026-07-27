from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from sqlalchemy import String, Float, Boolean, DateTime, Date, ForeignKey, Enum as SQLEnum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from services.database import Base


# --- ENUMS ---
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


# --- AUTH & USER ---
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole, native_enum=False), default=UserRole.SALES, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# --- INVENTORY & SPARE PARTS ---
class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vin: Mapped[str] = mapped_column(String(17), unique=True, index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(SQLEnum(VehicleStatus, native_enum=False), default=VehicleStatus.AVAILABLE, nullable=False)
    mileage: Mapped[int] = mapped_column(Integer, default=0)

    sales_record: Mapped[Optional["CarSale"]] = relationship("CarSale", back_populates="vehicle", uselist=False)


class SparePart(Base):
    __tablename__ = "spare_parts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    part_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    reorder_point: Mapped[int] = mapped_column(Integer, default=5)


# --- CRM & HR ---
class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    national_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    credit_score: Mapped[int] = mapped_column(Integer, default=650)
    segment: Mapped[str] = mapped_column(String(30), default="REGULAR")

    sales: Mapped[List["CarSale"]] = relationship("CarSale", back_populates="customer")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    base_salary: Mapped[float] = mapped_column(Float, nullable=False)
    performance_rating: Mapped[float] = mapped_column(Float, default=3.5)


# --- SALES & INSTALLMENTS ---
class CarSale(Base):
    __tablename__ = "car_sales"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    down_payment: Mapped[float] = mapped_column(Float, nullable=False)
    is_installment: Mapped[bool] = mapped_column(Boolean, default=False)
    sale_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="sales_record")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="sales")
    installment_plan: Mapped[Optional["InstallmentPlan"]] = relationship("InstallmentPlan", back_populates="sale", uselist=False)


class InstallmentPlan(Base):
    __tablename__ = "installment_plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("car_sales.id"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_balance: Mapped[float] = mapped_column(Float, nullable=False)
    months: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_payment: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[RiskLevel] = mapped_column(SQLEnum(RiskLevel, native_enum=False), default=RiskLevel.LOW)

    sale: Mapped["CarSale"] = relationship("CarSale", back_populates="installment_plan")
    payments: Mapped[List["InstallmentPayment"]] = relationship("InstallmentPayment", back_populates="plan", cascade="all, delete-orphan")


class InstallmentPayment(Base):
    __tablename__ = "installment_payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("installment_plans.id"), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[InstallmentStatus] = mapped_column(SQLEnum(InstallmentStatus, native_enum=False), default=InstallmentStatus.PENDING)

    plan: Mapped["InstallmentPlan"] = relationship("InstallmentPlan", back_populates="payments")


# --- GENERAL LEDGER & FINANCE ---
class Account(Base):
    __tablename__ = "chart_of_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(SQLEnum(AccountType, native_enum=False), nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entry_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    reference: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[List["JournalItem"]] = relationship("JournalItem", back_populates="entry", cascade="all, delete-orphan")


class JournalItem(Base):
    __tablename__ = "journal_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("chart_of_accounts.id"), nullable=False)
    debit: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[float] = mapped_column(Float, default=0.0)

    entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="items")
    account: Mapped["Account"] = relationship("Account")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    monthly_limit: Mapped[float] = mapped_column(Float, nullable=False)


# --- SERVICE CENTER ---
class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    vehicle_vin: Mapped[str] = mapped_column(String(17), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    technician_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=True)
    status: Mapped[WorkOrderStatus] = mapped_column(SQLEnum(WorkOrderStatus, native_enum=False), default=WorkOrderStatus.PENDING)
    labor_cost: Mapped[float] = mapped_column(Float, default=0.0)
    parts_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# --- AUDIT TRAIL ---
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)