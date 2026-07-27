import numpy as np
from sklearn.ensemble import RandomForestClassifier
from services.models import RiskLevel

class AIFinanceEngine:
    def __init__(self):
        # Pre-trained demonstration model initialization
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self._bootstrap_dummy_model()

    def _bootstrap_dummy_model(self):
        # Features: [Monthly Income, Installment Amount, Credit Score, Past Delays]
        X = np.array([
            [5000, 500, 750, 0],
            [2000, 800, 580, 3],
            [3500, 600, 640, 1],
            [10000, 1200, 800, 0],
            [1800, 900, 520, 4]
        ])
        y = np.array([0, 2, 1, 0, 2]) # 0: Low Risk, 1: Medium Risk, 2: High Risk
        self.model.fit(X, y)

    def predict_default_risk(self, monthly_income: float, installment_amount: float, credit_score: int, past_delays: int) -> dict:
        features = np.array([[monthly_income, installment_amount, credit_score, past_delays]])
        risk_class = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]

        risk_map = {0: RiskLevel.LOW, 1: RiskLevel.MEDIUM, 2: RiskLevel.HIGH}
        risk_level = risk_map[risk_class]
        confidence = float(np.max(probabilities))

        return {
            "risk_score": float(risk_class / 2.0), # Normalized score 0.0 - 1.0
            "risk_level": risk_level,
            "confidence_score": round(confidence, 2),
            "recommendation": "Require higher down payment" if risk_level == RiskLevel.HIGH else "Approve standard terms"
        }