"""
Enterprise Vehicle Inventory & Spare Parts Supply Chain Management Service
Provides CSV bulk ingestion, vehicle state-machine lifecycle management,
ABC Pareto Inventory Analysis, and Supply Chain Math (EOQ & Reorder Point).
"""

import math
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from services.models import Vehicle, SparePart, VehicleStatus
from services.csv_utils import safe_read_csv, sanitize_numeric_column, map_column
from services.analytics import AnalyticsEngine
from services.exceptions import (
    TEAMAIException,
    ValidationException,
    EntityNotFoundException,
    ConflictException
)

logger = logging.getLogger("TEAM_AI.InventoryService")


# ============================================================================
# DATA CONTRACTS & SCHEMAS
# ============================================================================

class VehicleCreateSchema(BaseModel):
    vin: str = Field(..., min_length=17, max_length=17, description="Standard 17-character Vehicle Identification Number")
    brand: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    year: int = Field(..., ge=1900, le=2100)
    purchase_price: float = Field(..., ge=0.0)
    selling_price: float = Field(..., ge=0.0)
    mileage: int = Field(default=0, ge=0)

    @field_validator("vin")
    def sanitize_vin(cls, v: str) -> str:
        return v.strip().upper()


class VehicleImportReport(BaseModel):
    success: bool
    vehicles_imported: int
    duplicates_skipped: int
    total_rows_read: int


class EOQCalculationResult(BaseModel):
    part_number: str
    part_name: str
    annual_demand: float
    economic_order_quantity_eoq: int
    reorder_point_units: int
    safety_stock_units: int
    replenishment_recommended: bool


class InventoryValuationMetrics(BaseModel):
    total_vehicles: int
    available_vehicles: int
    reserved_vehicles: int
    sold_vehicles: int
    total_asset_value_usd: float
    potential_revenue_usd: float
    unrealized_gross_margin_pct: float


# ============================================================================
# INVENTORY SERVICE ENGINE
# ============================================================================

class InventoryService:
    """
    Supply Chain & Inventory Management Service.
    Handles bulk vehicle imports, vehicle lifecycle state transitions, 
    spare parts ABC classification, and EOQ/ROP mathematical modeling.
    """

    # ------------------------------------------------------------------------
    # 1. BULK INGESTION ENGINE
    # ------------------------------------------------------------------------
    @staticmethod
    def import_inventory_csv(db: Session, file_bytes: bytes) -> VehicleImportReport:
        """
        Ingests vehicle records from uploaded CSV data.
        Employs vectorized operations and set-based lookup to eliminate N+1 DB queries.
        """
        try:
            df = safe_read_csv(file_bytes)
            if df.empty:
                raise ValidationException("The uploaded CSV file is empty.")

            # Resolve expected column mappings
            vin_col = map_column(df, ["vin", "vehicle_id", "serial", "vin_number"])
            brand_col = map_column(df, ["brand", "make", "manufacturer"])
            model_col = map_column(df, ["model", "series"])
            year_col = map_column(df, ["year", "model_year"])
            buy_price_col = map_column(df, ["purchase_price", "cost", "buy_price"])
            sell_price_col = map_column(df, ["selling_price", "price", "list_price"])

            # Vectorized Data Sanitization (Clean entire series before iteration)
            df["clean_vin"] = df[vin_col].astype(str).str.strip().str.upper()
            df["clean_buy_price"] = sanitize_numeric_column(df[buy_price_col])
            df["clean_sell_price"] = sanitize_numeric_column(df[sell_price_col])
            df["clean_year"] = sanitize_numeric_column(df[year_col]).fillna(2024).astype(int)

            # Drop invalid/empty VIN rows
            df = df[df["clean_vin"].str.len() > 0]

            # Single Query Set Lookup to prevent N+1 DB roundtrips
            candidate_vins = df["clean_vin"].unique().tolist()
            existing_vins = set(
                v[0] for v in db.query(Vehicle.vin).filter(Vehicle.vin.in_(candidate_vins)).all()
            )

            vehicles_to_insert: List[Vehicle] = []
            duplicates_count = 0
            seen_in_batch = set()

            for _, row in df.iterrows():
                vin_val = row["clean_vin"]

                # Collision check against existing DB records or intra-batch duplicates
                if vin_val in existing_vins or vin_val in seen_in_batch:
                    duplicates_count += 1
                    continue

                seen_in_batch.add(vin_val)

                vehicle = Vehicle(
                    vin=vin_val,
                    brand=str(row[brand_col]).strip(),
                    model=str(row[model_col]).strip(),
                    year=int(row["clean_year"]),
                    purchase_price=float(row["clean_buy_price"]),
                    selling_price=float(row["clean_sell_price"]),
                    status=VehicleStatus.AVAILABLE,
                    mileage=0
                )
                vehicles_to_insert.append(vehicle)

            # Bulk DB Operation
            if vehicles_to_insert:
                db.bulk_save_objects(vehicles_to_insert)
                db.commit()

            logger.info(f"Imported {len(vehicles_to_insert)} vehicles. Skipped {duplicates_count} duplicates.")

            return VehicleImportReport(
                success=True,
                vehicles_imported=len(vehicles_to_insert),
                duplicates_skipped=duplicates_count,
                total_rows_read=len(df)
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error importing vehicle inventory CSV: {str(e)}", exc_info=True)
            if isinstance(e, (ValidationException, TEAMAIException)):
                raise e
            raise TEAMAIException(f"Inventory Ingestion Failure: {str(e)}")

    # ------------------------------------------------------------------------
    # 2. VEHICLE LIFECYCLE MANAGEMENT
    # ------------------------------------------------------------------------
    @staticmethod
    def update_vehicle_status(db: Session, vin: str, new_status: VehicleStatus) -> Vehicle:
        """
        Updates a vehicle's operational status with state transition rules.
        """
        vehicle = db.query(Vehicle).filter(Vehicle.vin == vin.upper()).first()
        if not vehicle:
            raise EntityNotFoundException(f"Vehicle with VIN '{vin}' was not found.")

        # State transition validation logic
        if vehicle.status == VehicleStatus.SOLD and new_status != VehicleStatus.SOLD:
            raise ConflictException(f"Cannot change status of sold vehicle '{vin}'.")

        vehicle.status = new_status
        db.commit()
        db.refresh(vehicle)
        logger.info(f"Vehicle VIN {vin} status updated to {new_status.value}")
        return vehicle

    @staticmethod
    def get_inventory_valuation(db: Session) -> InventoryValuationMetrics:
        """
        Calculates aggregate asset valuation and unrealized gross margins across fleet.
        """
        agg = db.query(
            func.count(Vehicle.id).label("total"),
            func.coalesce(func.sum(case((Vehicle.status == VehicleStatus.AVAILABLE, 1), else_=0)), 0).label("available"),
            func.coalesce(func.sum(case((Vehicle.status == VehicleStatus.RESERVED, 1), else_=0)), 0).label("reserved"),
            func.coalesce(func.sum(case((Vehicle.status == VehicleStatus.SOLD, 1), else_=0)), 0).label("sold"),
            func.coalesce(func.sum(case((Vehicle.status == VehicleStatus.AVAILABLE, Vehicle.purchase_price), else_=0.0)), 0.0).label("asset_val"),
            func.coalesce(func.sum(case((Vehicle.status == VehicleStatus.AVAILABLE, Vehicle.selling_price), else_=0.0)), 0.0).label("potential_rev")
        ).first()

        asset_val = float(agg.asset_val)
        potential_rev = float(agg.potential_rev)
        potential_profit = potential_rev - asset_val
        margin_pct = (potential_profit / potential_rev * 100.0) if potential_rev > 0 else 0.0

        return InventoryValuationMetrics(
            total_vehicles=int(agg.total),
            available_vehicles=int(agg.available),
            reserved_vehicles=int(agg.reserved),
            sold_vehicles=int(agg.sold),
            total_asset_value_usd=round(asset_val, 2),
            potential_revenue_usd=round(potential_rev, 2),
            unrealized_gross_margin_pct=round(margin_pct, 2)
        )

    # ------------------------------------------------------------------------
    # 3. SPARE PARTS & SUPPLY CHAIN MATHEMATICS
    # ------------------------------------------------------------------------
    @staticmethod
    def get_spare_parts_abc_analysis(db: Session) -> List[Dict[str, Any]]:
        """
        Performs ABC Pareto Analysis on spare parts inventory.
        Categorizes parts into A (Top 80% Value), B (Next 15%), and C (Bottom 5%).
        """
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

        # Delegate Pareto calculation to Analytics Engine
        return AnalyticsEngine.classify_abc_inventory(
            df=df,
            cost_col="unit_cost",
            qty_col="stock_quantity",
            item_name_col="name"
        )

    @staticmethod
    def calculate_spare_part_eoq(
        db: Session,
        part_number: str,
        annual_demand: float,
        ordering_cost_per_order: float = 50.0,
        holding_cost_rate_pct: float = 0.20,
        lead_time_days: int = 7,
        service_factor_z: float = 1.65  # 95% service level
    ) -> EOQCalculationResult:
        """
        Calculates Economic Order Quantity (EOQ), Safety Stock, and Reorder Point (ROP).
        
        Math Formulas:
            EOQ = sqrt((2 * Demand * OrderingCost) / HoldingCost)
            Safety Stock = Z * sqrt(LeadTime) * (Daily Demand StdDev Estimate)
            ROP = (Daily Demand * LeadTime) + Safety Stock
        """
        part = db.query(SparePart).filter(SparePart.part_number == part_number).first()
        if not part:
            raise EntityNotFoundException(f"Spare part '{part_number}' not found.")

        if annual_demand <= 0:
            raise ValidationException("Annual demand must be greater than zero for EOQ calculation.")

        holding_cost_per_unit = max(0.01, part.unit_cost * holding_cost_rate_pct)
        
        # 1. Classical EOQ Calculation
        eoq = math.sqrt((2.0 * annual_demand * ordering_cost_per_order) / holding_cost_per_unit)

        # 2. Daily Demand & Safety Stock Calculation
        daily_demand = annual_demand / 365.0
        # Estimate daily demand standard deviation as 25% of average daily demand
        daily_demand_std_dev = daily_demand * 0.25 
        safety_stock = service_factor_z * math.sqrt(lead_time_days) * daily_demand_std_dev
        
        # 3. Reorder Point (ROP)
        reorder_point = (daily_demand * lead_time_days) + safety_stock

        needs_replenishment = part.stock_quantity <= math.ceil(reorder_point)

        return EOQCalculationResult(
            part_number=part.part_number,
            part_name=part.name,
            annual_demand=round(annual_demand, 2),
            economic_order_quantity_eoq=math.ceil(eoq),
            reorder_point_units=math.ceil(reorder_point),
            safety_stock_units=math.ceil(safety_stock),
            replenishment_recommended=needs_replenishment
        )
