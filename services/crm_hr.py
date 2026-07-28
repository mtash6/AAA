import logging
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from services.models import Customer, Employee

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# PYDANTIC INPUT VALIDATION SCHEMAS
# --------------------------------------------------------------------------

class CustomerCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    national_id: str = Field(..., min_length=5, max_length=50)
    phone: str = Field(..., min_length=7, max_length=20)
    email: EmailStr
    credit_score: int = Field(default=600, ge=300, le=850)


class EmployeeCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    position: str = Field(..., min_length=2, max_length=100)
    department: str = Field(..., min_length=2, max_length=100)
    base_salary: float = Field(..., ge=0.0)


# --------------------------------------------------------------------------
# CRM SERVICE
# --------------------------------------------------------------------------

class CRMService:
    """Service handling Customer Relationship Management (CRM) domain operations."""

    @staticmethod
    def create_customer(db: Session, schema: CustomerCreate) -> Customer:
        """
        Creates and persists a new customer record with constraint verification.
        """
        # Check for existing duplicate national ID or email before inserting
        existing = db.query(Customer).filter(
            (Customer.national_id == schema.national_id) | (Customer.email == schema.email)
        ).first()

        if existing:
            field = "National ID" if existing.national_id == schema.national_id else "Email address"
            raise ValueError(f"A customer with this {field} already exists.")

        cust = Customer(
            full_name=schema.full_name,
            national_id=schema.national_id,
            phone=schema.phone,
            email=schema.email,
            credit_score=schema.credit_score,
        )

        try:
            db.add(cust)
            db.commit()
            db.refresh(cust)
            logger.info(f"Created Customer ID {cust.id} ({cust.full_name})")
            return cust
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error creating customer: {e}")
            raise ValueError("Failed to create customer due to a database constraint error.")
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error creating customer: {e}")
            raise e

    @staticmethod
    def get_customer_by_id(db: Session, customer_id: int) -> Optional[Customer]:
        return db.query(Customer).filter(Customer.id == customer_id).first()

    @staticmethod
    def get_customer_by_national_id(db: Session, national_id: str) -> Optional[Customer]:
        return db.query(Customer).filter(Customer.national_id == national_id).first()


# --------------------------------------------------------------------------
# HR SERVICE
# --------------------------------------------------------------------------

class HRService:
    """Service handling Human Resources (HR) employee lifecycle operations."""

    @staticmethod
    def create_employee(db: Session, schema: EmployeeCreate) -> Employee:
        """
        Creates and persists a new employee record.
        """
        emp = Employee(
            full_name=schema.full_name,
            position=schema.position,
            department=schema.department,
            base_salary=schema.base_salary,
        )

        try:
            db.add(emp)
            db.commit()
            db.refresh(emp)
            logger.info(f"Created Employee ID {emp.id} ({emp.full_name}) - Dept: {emp.department}")
            return emp
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error creating employee: {e}")
            raise ValueError("Failed to create employee due to a database constraint error.")
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error creating employee: {e}")
            raise e

    @staticmethod
    def get_employee_by_id(db: Session, employee_id: int) -> Optional[Employee]:
        return db.query(Employee).filter(Employee.id == employee_id).first()

    @staticmethod
    def list_employees_by_department(db: Session, department: str) -> List[Employee]:
        return db.query(Employee).filter(Employee.department == department).all()
