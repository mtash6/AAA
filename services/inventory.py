"""
Inventory & Spare Parts Management Service
"""

from sqlalchemy.orm import Session
from services.models import Vehicle, SparePart, VehicleStatus
from services.csv_utils import safe_read_csv, sanitize_numeric_column, map_column
from services.analytics import AnalyticsEngine
from services.exceptions import TEAMAIException


class InventoryService:

    @staticmethod
    def import_inventory_csv(db: Session, file_bytes: bytes) -> dict:
        """Robustly ingests vehicle inventory records from uploaded CSV bytes."""
        try:
            df = safe_read_csv(file_bytes)

            vin_col = map_column(df, ["vin", "vehicle_id", "serial"])
            brand_col = map_column(df, ["brand", "make", "manufacturer"])
            model_col = map_column(df, ["model", "series"])
            year_col = map_column(df, ["year", "model_year"])
            buy_price_col = map_column(df, ["purchase_price", "cost", "buy_price"])
            sell_price_col = map_column(df, ["selling_price", "price", "list_price"])

            count = 0
            for _, row in df.iterrows():
                vin_val = str(row[vin_col]).strip().upper()
                if not vin_val or db.query(Vehicle).filter(Vehicle.vin == vin_val).first():
                    continue  # Skip invalid or duplicate VINs

                buy_p = float(sanitize_numeric_column(pd.Series([row[buy_price_col]]))[0])
                sell_p = float(sanitize_numeric_column(pd.Series([row[sell_price_col]]))[0])
                year_v = int(float(sanitize_numeric_column(pd.Series([row[year_col]]))[0])) or 2024

                vehicle = Vehicle(
                    vin=vin_val,
                    brand=str(row[brand_col]).strip(),
                    model=str(row[model_col]).strip(),
                    year=year_v,
                    purchase_price=buy_p,
                    selling_price=sell_p,
                    status=VehicleStatus.AVAILABLE,
                    mileage=0
                )
                db.add(vehicle)
                count += 1

            db.commit()
            return {"success": True, "vehicles_imported": count, "total_rows_read": len(df)}
        except Exception as e:
            db.rollback()
            raise TEAMAIException(f"Inventory Ingestion Error: {str(e)}")

    @staticmethod
    def get_spare_parts_abc_analysis(db: Session) -> list:
        """Runs ABC Pareto analysis on stored spare parts."""
        parts = db.query(SparePart).all()
        if not parts:
            return []

        data = [{
            "part_number": p.part_number,
            "name": p.name,
            "unit_cost": p.unit_cost,
            "stock_quantity": p.stock_quantity
        } for p in parts]

        df = pd.DataFrame(data)
        return AnalyticsEngine.classify_abc_inventory(
            df=df,
            cost_col="unit_cost",
            qty_col="stock_quantity",
            item_name_col="name"
        )