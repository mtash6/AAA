import numpy as np
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.pipeline import Pipeline

# Fallback/Mock for services.models import if running standalone
try:
    from services.models import RiskLevel
except ImportError:
    class RiskLevel(str, Enum):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"


# --------------------------------------------------------------------------
# PYDANTIC RESPONSE SCHEMAS
# --------------------------------------------------------------------------

class CreditRiskAssessment(BaseModel):
    risk_level: RiskLevel
    probability_of_default: float = Field(..., ge=0.0, le=1.0)
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Normalized risk score (0=safe, 100=extreme risk)")
    confidence_pct: float = Field(..., ge=0.0, le=100.0)
    debt_to_income_ratio: float
    expected_loss_usd: float = Field(..., description="Calculated Expected Loss: PD * LGD * EAD")
    risk_drivers: List[str]


class FraudAssessment(BaseModel):
    is_fraudulent: bool
    anomaly_score: float = Field(..., ge=0.0, le=100.0, description="Normalized anomaly score")
    confidence_pct: float
    risk_factors: List[str]


class CustomerSegmentResult(BaseModel):
    segment: str  # "PREMIUM", "REGULAR", "BUDGET"
    cluster_id: int
    distance_to_centroid: float


# --------------------------------------------------------------------------
# ENTERPRISE AI ENGINE
# --------------------------------------------------------------------------

class EnterpriseAIEngine:
    """
    Advanced Machine Learning Engine for Financial Credit Risk, Multi-Signal
    Fraud Anomaly Detection, and Dynamic Centroid Customer Segmentation.
    """

    def __init__(self):
        self._init_credit_model()
        self._init_fraud_pipeline()

    # ----------------------------------------------------------------------
    # 1. CREDIT RISK ASSESSMENT
    # ----------------------------------------------------------------------

    def _init_credit_model(self):
        """Builds a gradient boosting credit risk model with engineered ratios."""
        self.credit_model = HistGradientBoostingClassifier(
            max_iter=50,
            learning_rate=0.1,
            random_state=42
        )

        # Base Features: [income, installment, credit_score, past_delays, DTI_ratio, PTI_ratio]
        X_train = np.array([
            [8000.0, 400.0, 780, 0, 0.05, 0.05],   # Low Risk
            [5000.0, 500.0, 720, 0, 0.10, 0.10],   # Low Risk
            [3500.0, 800.0, 640, 1, 0.22, 0.22],   # Medium Risk
            [2500.0, 900.0, 590, 2, 0.36, 0.36],   # High Risk
            [1800.0, 850.0, 520, 4, 0.47, 0.47],   # High Risk
            [12000.0, 1500.0, 810, 0, 0.12, 0.12], # Low Risk
            [4000.0, 1400.0, 610, 3, 0.35, 0.35],  # High Risk
        ])
        y_train = np.array([0, 0, 1, 2, 2, 0, 2])  # 0: Low, 1: Medium, 2: High
        self.credit_model.fit(X_train, y_train)

    def predict_credit_risk(
        self, 
        monthly_income: float, 
        installment_amount: float, 
        credit_score: int, 
        past_delays: int,
        exposure_amount: float = 10000.0
    ) -> CreditRiskAssessment:
        """
        Calculates credit default probability, expected loss, and primary risk drivers.
        """
        income = max(monthly_income, 1.0)
        dti = round(installment_amount / income, 4)
        pti = round((installment_amount * 12) / (income * 12), 4)

        features = np.array([[monthly_income, installment_amount, credit_score, past_delays, dti, pti]])
        
        pred_class = int(self.credit_model.predict(features)[0])
        probs = self.credit_model.predict_proba(features)[0]

        risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        
        # Calculate Probability of Default (PD) as weighted probability of High/Medium risk
        pd_score = float(probs[2] * 1.0 + probs[1] * 0.4)
        
        # Financial Risk Math: Expected Loss (EL) = PD * Loss Given Default (assume 45%) * Exposure
        lgd = 0.45
        expected_loss = round(pd_score * lgd * exposure_amount, 2)

        # Risk Factor Diagnostics
        risk_drivers = []
        if credit_score < 620:
            risk_drivers.append("Subprime Credit Score (<620)")
        if dti > 0.35:
            risk_drivers.append(f"High Debt-to-Income Ratio ({dti * 100:.1f}%)")
        if past_delays > 0:
            risk_drivers.append(f"Historical Delinquencies ({past_delays} past late payments)")

        return CreditRiskAssessment(
            risk_level=risk_levels[pred_class],
            probability_of_default=round(pd_score, 4),
            risk_score=round(pd_score * 100, 2),
            confidence_pct=round(float(np.max(probs)) * 100, 1),
            debt_to_income_ratio=dti,
            expected_loss_usd=expected_loss,
            risk_drivers=risk_drivers or ["Operational parameters within healthy limits."]
        )

    # ----------------------------------------------------------------------
    # 2. MULTI-SIGNAL FRAUD DETECTION
    # ----------------------------------------------------------------------

    def _init_fraud_pipeline(self):
        """Initializes a scaled Isolation Forest for multivariate fraud analytics."""
        self.fraud_pipeline = Pipeline([
            ("scaler", RobustScaler()),
            ("detector", IsolationForest(contamination=0.08, random_state=42))
        ])

        # Features: [tx_amount, user_avg_amount, tx_velocity_1h, z_score_deviation]
        baseline_txs = np.array([
            [50.0, 45.0, 1, 0.1],
            [120.0, 100.0, 2, 0.2],
            [15.0, 20.0, 1, -0.3],
            [250.0, 200.0, 3, 0.5],
            [500.0, 480.0, 2, 0.1],
            [12000.0, 150.0, 14, 8.5],  # Outlier
            [85.0, 90.0, 1, -0.1],
        ])
        self.fraud_pipeline.fit(baseline_txs)

    def detect_fraudulent_transaction(
        self, 
        amount: float, 
        user_avg_amount: float = 100.0, 
        tx_velocity_1h: int = 1
    ) -> FraudAssessment:
        """
        Evaluates transaction context against Isolation Forest & Statistical Z-Scores.
        """
        # Statistical Deviation Signal
        std_dev = max(user_avg_amount * 0.5, 10.0)
        z_score = (amount - user_avg_amount) / std_dev

        features = np.array([[amount, user_avg_amount, tx_velocity_1h, z_score]])
        
        # ML Outlier Signal (-1 = Outlier, 1 = Normal)
        is_anomaly_ml = self.fraud_pipeline.predict(features)[0] == -1
        raw_score = self.fraud_pipeline.named_steps["detector"].decision_function(features)[0]
        
        # Normalize score to 0 - 100
        anomaly_intensity = float(np.clip((0.5 - raw_score) * 100, 0.0, 100.0))
        is_fraud = is_anomaly_ml or z_score > 3.5 or tx_velocity_1h > 10

        risk_factors = []
        if z_score > 3.0:
            risk_factors.append(f"Severe amount deviation ({z_score:.1f}σ above average)")
        if tx_velocity_1h > 8:
            risk_factors.append(f"High velocity rate ({tx_velocity_1h} transactions/hour)")
        if amount > 10000.0:
            risk_factors.append("High-Value transaction threshold breach")

        return FraudAssessment(
            is_fraudulent=is_fraud,
            anomaly_score=round(anomaly_intensity, 2),
            confidence_pct=round(min(80.0 + anomaly_intensity * 0.2, 99.9), 1),
            risk_factors=risk_factors or ["Transaction behavior is nominal."]
        )

    # ----------------------------------------------------------------------
    # 3. DYNAMIC CENTROID CUSTOMER SEGMENTATION
    # ----------------------------------------------------------------------

    def segment_customers(self, customer_data: List[List[float]]) -> List[CustomerSegmentResult]:
        """
        Segments customers into PREMIUM, REGULAR, or BUDGET tiers using Scaled K-Means.
        Ensures centroid labels are mathematically sorted by segment value magnitude.
        """
        if not customer_data or len(customer_data) < 3:
            return [
                CustomerSegmentResult(segment="REGULAR", cluster_id=1, distance_to_centroid=0.0)
                for _ in range(len(customer_data))
            ]

        X = np.array(customer_data)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        centroids = kmeans.cluster_centers_

        # Dynamic Centroid Ordering: Rank cluster centers by overall magnitude
        centroid_magnitudes = np.linalg.norm(centroids, axis=1)
        sorted_cluster_indices = np.argsort(centroid_magnitudes)  # [lowest, middle, highest]

        # Map cluster IDs -> sorted ranking
        rank_to_label = {
            sorted_cluster_indices[2]: "PREMIUM",
            sorted_cluster_indices[1]: "REGULAR",
            sorted_cluster_indices[0]: "BUDGET",
        }

        results = []
        for i, (point_scaled, cluster_id) in enumerate(zip(X_scaled, labels)):
            centroid = centroids[cluster_id]
            dist = float(np.linalg.norm(point_scaled - centroid))
            results.append(
                CustomerSegmentResult(
                    segment=rank_to_label[cluster_id],
                    cluster_id=int(cluster_id),
                    distance_to_centroid=round(dist, 4)
                )
            )

        return results
