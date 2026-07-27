"""
Triple A Enterprise Management AI System - Interactive CLI Portal
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from services.database import engine, Base, SessionLocal
from services.models import User, UserRole, Vehicle, VehicleStatus, SparePart, Account
from services.auth import hash_password
from services.finnance import FinanceService
from services.inventory import InventoryService
from services.ai_advisor import AIBusinessAdvisor
from services.exec_finance import ExecutiveAnalyticsEngine
from services.charts import ChartEngine
from services.analytics import AnalyticsEngine


def banner():
    print("=" * 80)
    print("  TRIPLE A ENTERPRISE MANAGEMENT AI SYSTEM - CLI PORTAL v5.0")
    print("=" * 80)


def print_menu():
    print("\nSelect Operation:")
    print("  [1] Initialize Database & Seed Base Records")
    print("  [2] View Executive Health Score & Metrics")
    print("  [3] Run Strategic AI Advisor")
    print("  [4] Inventory: Query Vehicles & Spare Parts")
    print("  [5] Algorithm: Run Pareto ABC Inventory Analysis")
    print("  [6] Algorithm: Run Linear Sales Forecasting")
    print("  [7] Finance: View General Ledger Balances")
    print("  [8] Ingestion: Test Ingest Inventory CSV")
    print("  [9] Ingestion: Test Ingest Transactions CSV (With IQR Outlier Detection)")
    print(" [10] Visualization: Render Executive Multi-Chart Dashboard Suite")
    print("  [0] Exit")
    print("-" * 80)


def seed_database(db: Session):
    print("\n[+] Initializing Database Schemas...")
    os.makedirs("./outputs", exist_ok=True)
    os.makedirs("./uploads", exist_ok=True)
    Base.metadata.create_all(bind=engine)

    FinanceService.seed_default_accounts(db)

    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(
            username="admin",
            email="admin@aaa-agency.com",
            hashed_password=hash_password("Admin@12345"),
            role=UserRole.ADMIN,
            is_active=True
        ))
        print("  -> Created Admin Account: admin / Admin@12345")

    if db.query(Vehicle).count() == 0:
        db.add(Vehicle(
            vin="1HGCR2F83HA000001",
            brand="Toyota",
            model="Camry",
            year=2024,
            purchase_price=22000.0,
            selling_price=28500.0,
            status=VehicleStatus.AVAILABLE,
            mileage=15
        ))
        print("  -> Created Sample Vehicle.")

    if db.query(SparePart).count() == 0:
        parts = [
            SparePart(part_number="SP-001", name="Brake Pads Set", category="Brakes", unit_cost=45.0, selling_price=95.0, stock_quantity=100),
            SparePart(part_number="SP-002", name="Engine Oil Filter", category="Engine", unit_cost=8.0, selling_price=22.0, stock_quantity=250),
            SparePart(part_number="SP-003", name="Transmission Kit", category="Transmission", unit_cost=450.0, selling_price=850.0, stock_quantity=12)
        ]
        db.add_all(parts)
        print("  -> Created Sample Spare Parts.")

    db.commit()
    print("[✓] Initialization complete.\n")


def run_abc_analysis(db: Session):
    print("\n--- Algorithm: ABC Pareto Inventory Analysis ---")
    results = InventoryService.get_spare_parts_abc_analysis(db)
    if not results:
        print("  No spare parts found. Seed database first [Option 1].")
        return
    
    print(f"  {'Item Name':<25} | {'Cost ($)':<10} | {'Stock':<8} | {'Total Val ($)':<12} | {'Class'}")
    print("  " + "-" * 70)
    for r in results:
        print(f"  {r['name']:<25} | ${r['unit_cost']:<9.2f} | {r['stock_quantity']:<8} | ${r['total_value']:<11.2f} | Class {r['abc_class']}")


def run_sales_forecast():
    print("\n--- Algorithm: Predictive Linear Sales Trend Forecasting ---")
    sample_sales = [12000.0, 14500.0, 13800.0, 16200.0, 18900.0, 21000.0]
    print(f"  Historical Monthly Revenues: {sample_sales}")
    
    res = AnalyticsEngine.forecast_linear_trend(sample_sales, periods_ahead=3)
    print(f"  Trend Direction : {res.get('trend_direction')}")
    print(f"  Slope (Growth)  : ${res.get('slope'):,.2f} / month")
    print(f"  Forecast Next 3 Months: {res.get('forecast_next_periods')}")


def import_csv_cli(db: Session, target: str):
    path = input(f"\nEnter complete path to {target.upper()} CSV file: ").strip()
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return

    try:
        with open(path, "rb") as f:
            b = f.read()

        if target == "inventory":
            res = InventoryService.import_inventory_csv(db, b)
        else:
            res = FinanceService.import_transactions_csv(db, b)

        print(f"\n[✓] Ingestion Result: {res}")
    except Exception as e:
        print(f"\n[!] Ingestion error: {str(e)}")


def render_dashboard_suite():
    print("\n--- Visualization: Rendering Executive Dashboard Suite ---")
    sample_csv = (
        "category,revenue,cost\n"
        "Sedans,85000,52000\n"
        "SUVs,120000,78000\n"
        "Trucks,95000,61000\n"
        "EVs,110000,72000\n"
        "Spare Parts,45000,21000\n"
        "Services,68000,29000"
    )
    out_path = "./outputs/executive_dashboard_suite.png"
    try:
        res = ChartEngine.generate_multi_chart_dashboard(
            file_bytes=sample_csv.encode("utf-8"),
            save_path=out_path
        )
        print(f"[✓] Dashboard Suite generated with {res.get('charts_generated')} charts!")
        print(f"    Saved to: {out_path}")
    except Exception as e:
        print(f"[!] Dashboard generation error: {str(e)}")


def main():
    banner()
    db = SessionLocal()

    try:
        while True:
            print_menu()
            choice = input("Select option [0-10]: ").strip()

            if choice == "1":
                seed_database(db)
            elif choice == "2":
                print("\nExecutive Health:", ExecutiveAnalyticsEngine.compute_business_health_score(db))
            elif choice == "3":
                print("\nAI Recommendations:", AIBusinessAdvisor.generate_recommendations(db))
            elif choice == "4":
                print(f"Vehicles Count: {db.query(Vehicle).count()} | Spare Parts Count: {db.query(SparePart).count()}")
            elif choice == "5":
                run_abc_analysis(db)
            elif choice == "6":
                run_sales_forecast()
            elif choice == "7":
                for acc in db.query(Account).all():
                    print(f"  [{acc.code}] {acc.name:<30} Balance: ${acc.balance:,.2f}")
            elif choice == "8":
                import_csv_cli(db, "inventory")
            elif choice == "9":
                import_csv_cli(db, "finance")
            elif choice == "10":
                render_dashboard_suite()
            elif choice == "0":
                print("\nExiting CLI. Goodbye!")
                break
    finally:
        db.close()


if __name__ == "__main__":
    main()