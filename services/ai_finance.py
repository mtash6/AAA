"""
AI Finance Engine: Credit Risk & Default Probability Scoring
Evaluates customer creditworthiness using Random Forest Classification,
engineered Debt-to-Income (DTI) metrics, and dynamic risk scoring.
"""

import logging
from enum import Enum
from typing import Dict, Any, Optional, Union
import numpy as np
from pydantic import BaseModel, Field, field_validator
from sklearn.ensemble import RandomForestClassifier

from services.models import RiskLevel
from services.exceptions import TEAMAIException, ValidationException

logger = logging.getLogger("TEAM_AI.AIFinanceEngine")


# --------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# --------------------------------------------------------------------------

class RiskAssessmentInput(BaseModel):
    monthly_income: float = Field(..., ge=0.0, description="Monthly income in USD/local currency")
    installment_amount: float = Field(..., ge=0.0, description="Requested monthly installment")
    credit_score: int = Field(..., ge=300, le=850, description="FICO/Credit score (300-850)")
    past_delays: int = Field(..., ge=0, description="Count of past payment delays (30+ days)")

    @field_validator("monthly_income")
    def validate_income_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Monthly income must be greater than zero for credit assessment.")
        return v


class RiskAssessmentOutput(BaseModel):
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Continuous risk score [0.0 = Low, 1.0 = High]")
    risk_level: RiskLevel
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence probability")
    dti_ratio_pct: float = Field(..., description="Debt-to-Income ratio percentage")
    recommendation: str


# --------------------------------------------------------------------------
# AI FINANCE ENGINE
# --------------------------------------------------------------------------

class AIFinanceEngine:
    """
    AI-powered credit scoring engine. Evaluates default risk based on 
    applicant financial parameters, credit history, and DTI metrics.
    """

    # Risk level mappings: 0 -> LOW, 1 -> MEDIUM, 2 -> HIGH
    CLASS_TO_RISK_MAP: Dict[int, RiskLevel] = {
        0: RiskLevel.LOW,
        1: RiskLevel.MEDIUM,
        2: RiskLevel.HIGH
    }

    RISK_CLASS_WEIGHTS: Dict[int, float] = {
        0: 0.0,   # Low Risk Weight
        1: 0.5,   # Medium Risk Weight
        2: 1.0    # High Risk Weight
    }

    HIGH_RISK_THRESHOLD: float = 0.70

    def __init__(self, model: Optional[RandomForestClassifier] = None):
        """
        Initializes the AI Finance Engine.
        """
        if model:
            self.model = model
            logger.info("Pre-trained production model loaded successfully.")
        else:
            logger.warning("No pre-trained model provided. Bootstrapping dummy model for dev/testing.")
            self.model = self._bootstrap_dummy_model()

    @classmethod
    def load_model(cls, model_path: str) -> "AIFinanceEngine":
        """Loads a pre-trained model artifact from disk using joblib."""
        try:
            import joblib
            loaded_model = joblib.load(model_path)
            logger.info(f"Loaded ML model artifact from {model_path}")
            return cls(model=loaded_model)
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise TEAMAIException(f"Could not load ML model artifact: {str(e)}")

    @staticmethod
    def _bootstrap_dummy_model() -> RandomForestClassifier:
        """
        Bootstraps a preliminary model trained with synthetic financial data.
        Features: [Monthly Income, Installment Amount, Credit Score, Past Delays, DTI Ratio]
        """
        # [income, installment, credit_score, past_delays, dti_ratio]
        X = np.array([
            [5000.0, 500.0, 750, 0, 0.10],
            [2000.0, 800.0, 580, 3, 0.40],
            [3500.0, 600.0, 640, 1, 0.17],
            [10000.0, 1200.0, 800, 0, 0.12],
            [1800.0, 900.0, 520, 4, 0.50]
        ])
        y = np.array([0, 2, 1, 0, 2])  # 0: Low, 1: Medium, 2: High

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        return model

    def _extract_features(self, payload: RiskAssessmentInput) -> np.ndarray:
        """Calculates engineered features (e.g., DTI Ratio) and returns feature vector."""
        dti_ratio = payload.installment_amount / payload.monthly_income
        return np.array([[
            payload.monthly_income,
            payload.installment_amount,
            payload.credit_score,
            payload.past_delays,
            dti_ratio
        ]])

    def predict_default_risk(
        self, 
        monthly_income: float, 
        installment_amount: float, 
        credit_score: int, 
        past_delays: int
    ) -> RiskAssessmentOutput:
        """
        Predicts customer default risk based on applicant financial metrics.
        """
        # 1. Validate Inputs via Pydantic Contract
        try:
            payload = RiskAssessmentInput(
                monthly_income=monthly_income,
                installment_amount=installment_amount,
                credit_score=credit_score,
                past_delays=past_delays
            )
        except Exception as err:
            logger.warning(f"Validation failure for risk assessment: {err}")
            raise ValidationException(f"Invalid applicant inputs: {str(err)}")

        try:
            # 2. Feature Extraction & Engineering
            features = self._extract_features(payload)
            dti_pct = (payload.installment_amount / payload.monthly_income) * 100.0

            # 3. Model Inference
            predicted_class = int(self.model.predict(features)[0])
            probabilities = self.model.predict_proba(features)[0]

            # 4. Safely Map Probabilities to Class Weights (Fixes Array Shape Mismatch)
            classes = self.model.classes_
            class_prob_map = dict(zip(classes, probabilities))
            
            # Weighted average risk score computation
            continuous_risk_score = sum(
                prob * self.RISK_CLASS_WEIGHTS.get(cls_idx, 0.5)
                for cls_idx, prob in class_prob_map.items()
            )

            # 5. Risk Level Assignment & Recommendation
            risk_level = self.CLASS_TO_RISK_MAP.get(predicted_class, RiskLevel.MEDIUM)
            confidence = float(np.max(probabilities))
            recommendation = self._generate_recommendation(risk_level, continuous_risk_score, dti_pct)

            logger.info(
                f"Credit Assessment Completed: Risk={risk_level.value} | "
                f"Score={continuous_risk_score:.2f} | DTI={dti_pct:.1f}%"
            )

            return RiskAssessmentOutput(
                risk_score=round(continuous_risk_score, 2),
                risk_level=risk_level,
                confidence_score=round(confidence, 2),
                dti_ratio_pct=round(dti_pct, 2),
                recommendation=recommendation
            )

        except Exception as e:
            logger.error(f"Inference error in AIFinanceEngine: {str(e)}", exc_info=True)
            raise TEAMAIException(f"Credit risk prediction error: {str(e)}")

    @classmethod
    def _generate_recommendation(
        cls, 
        risk_level: RiskLevel, 
        risk_score: float, 
        dti_pct: float
    ) -> str:
        """Generates contextual business recommendations based on risk and DTI."""
        if risk_level == RiskLevel.HIGH or risk_score >= cls.HIGH_RISK_THRESHOLD:
            return "REJECT OR REQUIRE CO-SIGNER: High probability of default. Require minimum 30% down payment."
        
        if dti_pct > 45.0:
            return "CONDITIONALLY APPROVED: High Debt-to-Income ratio (>45%). Require proof of additional liquid reserves."

        if risk_level == RiskLevel.MEDIUM:
            return "APPROVE WITH STANDARD TERMS: Moderate risk profile. Standard interest rate applies."

        return "EXPEDITED APPROVAL: Low risk profile. Eligible for prime interest rate tiers."
