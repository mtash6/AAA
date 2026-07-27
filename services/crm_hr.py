from sqlalchemy.orm import Session
from services.models import Customer, Employee


class CRMService:
    @staticmethod
    def create_customer(db: Session, name: str, national_id: str, phone: str, email: str, credit_score: int) -> Customer:
        cust = Customer(full_name=name, national_id=national_id, phone=phone, email=email, credit_score=credit_score)
        db.add(cust)
        db.commit()
        db.refresh(cust)
        return cust


class HRService:
    @staticmethod
    def create_employee(db: Session, name: str, position: str, department: str, salary: float) -> Employee:
        emp = Employee(full_name=name, position=position, department=department, base_salary=salary)
        db.add(emp)
        db.commit()
        db.refresh(emp)
        return emp