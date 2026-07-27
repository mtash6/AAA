import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from services.database import engine, Base, get_db
from services.models import UserRole, User
from services.schemas import UserCreate, Token, ExecutiveHealthResponse
from services.auth import hash_password, verify_password, create_access_token, require_roles
from services.inventory import InventoryService
from services.finnance import FinanceService
from services.charts import ChartEngine
from services.analytics import AnalyticsEngine
from services.ai_advisor import AIBusinessAdvisor
from services.exec_finance import ExecutiveAnalyticsEngine
from services.logger import RequestLoggingMiddleware, logger
from services.exceptions import register_exception_handlers, TEAMAIException


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Triple A Enterprise Systems Engine...")
    os.makedirs("./outputs", exist_ok=True)
    os.makedirs("./uploads", exist_ok=True)
    
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        FinanceService.seed_default_accounts(db)
        
    logger.info("Database schemas and Chart of Accounts initialized.")
    yield


app = FastAPI(
    title="Triple A Enterprise Management AI System",
    version="5.0.0",
    description="Enterprise Platform with Robust CSV Ingestion, Multi-Chart Analytics Suite & Predictive Algorithms",
    lifespan=lifespan
)

register_exception_handlers(app)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "HEALTHY", "version": "5.0.0"}


# --- AUTH ---
@app.post("/api/v1/auth/register", tags=["Auth"])
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_data.username).first():
        raise TEAMAIException("Username is already registered.", code="USER_EXISTS")
    
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role
    )
    db.add(user)
    db.commit()
    return {"success": True, "message": "User registered successfully."}


@app.post("/api/v1/auth/token", response_model=Token, tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise TEAMAIException("Invalid login credentials provided.", code="INVALID_CREDENTIALS")
    
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}


# --- VISUALIZATION & CHARTS ---
@app.post("/api/v1/charts/single", tags=["Analytics & Charts"])
async def generate_single_chart(
    file: UploadFile = File(...),
    x_col: str = Form("string"),
    y_col: str = Form("string"),
    chart_type: str = Form("bar")
):
    contents = await file.read()
    return ChartEngine.generate_chart_from_csv(contents, x_col=x_col, y_col=y_col, chart_type=chart_type)


@app.post("/api/v1/charts/dashboard-suite", tags=["Analytics & Charts"])
async def generate_dashboard_suite(file: UploadFile = File(...)):
    """Generates a 4-chart executive dashboard suite from uploaded CSV."""
    contents = await file.read()
    return ChartEngine.generate_multi_chart_dashboard(contents)


# --- DATA ANALYSIS ALGORITHMS ---
@app.post("/api/v1/analytics/detect-anomalies", tags=["Algorithms"])
async def detect_csv_anomalies(file: UploadFile = File(...), column_name: str = Form("amount")):
    """Runs IQR Anomaly Detection algorithm on uploaded CSV data."""
    from services.csv_utils import safe_read_csv, sanitize_numeric_column, map_column
    contents = await file.read()
    df = safe_read_csv(contents)
    target_col = map_column(df, [column_name, "amount", "revenue", "price", "cost"])
    df[target_col] = sanitize_numeric_column(df[target_col])
    return AnalyticsEngine.detect_anomalies_iqr(df, target_col)


@app.get("/api/v1/analytics/spare-parts-abc", tags=["Algorithms"])
def get_spare_parts_abc(db: Session = Depends(get_db)):
    """Runs ABC Pareto classification on spare parts inventory."""
    return InventoryService.get_spare_parts_abc_analysis(db)


# --- CSV INGESTION ---
@app.post("/api/v1/inventory/upload-csv", tags=["Inventory"])
async def upload_inventory_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    return InventoryService.import_inventory_csv(db, contents)


@app.post("/api/v1/finance/upload-csv", tags=["Finance"])
async def upload_finance_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    return FinanceService.import_transactions_csv(db, contents)


# --- EXECUTIVE ---
@app.get("/api/v1/ai/advisor-recommendations", tags=["Executive"])
def get_ai_recommendations(db: Session = Depends(get_db)):
    return {"success": True, "recommendations": AIBusinessAdvisor.generate_recommendations(db)}


@app.get("/api/v1/executive/health", response_model=ExecutiveHealthResponse, tags=["Executive"])
def get_executive_health(db: Session = Depends(get_db)):
    return ExecutiveAnalyticsEngine.compute_business_health_score(db)
    if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
