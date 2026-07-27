import numpy as np
from typing import Dict, Any, List
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.cluster import KMeans
from services.models import RiskLevel


class AIEngine:
    def __init__(self):
        # Synthetic fit for baseline credit model
        self.credit_model = RandomForestClassifier(n_estimators=20, random_state=42)
        X_train = np.array([
            [5000, 500, 750, 0],
            [2000, 800, 580, 3],
            [10000, 1200, 800, 0],
            [1500, 600, 520, 4]
        ])
        y_train = np.array([0, 2, 0, 2])  # 0: Low, 1: Medium, 2: High
        self.credit_model.fit(X_train, y_train)

        # Isolation Forest for Fraud Detection
        self.fraud_detector = IsolationForest(contamination=0.1, random_state=42)
        dummy_txs = np.array([[100], [200], [150], [500], [12000], [180]])
        self.fraud_detector.fit(dummy_txs)

    def predict_credit_risk(self, monthly_income: float, installment_amount: float, credit_score: int, past_delays: int) -> Dict[str, Any]:
        features = np.array([[monthly_income, installment_amount, credit_score, past_delays]])
        pred_class = self.credit_model.predict(features)[0]
        probs = self.credit_model.predict_proba(features)[0]

        risk_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        return {
            "risk_level": risk_levels[pred_class],
            "risk_score": float(round((1 - probs[pred_class]) * 100, 2)),
            "confidence_pct": float(round(np.max(probs) * 100, 1))
        }

    def detect_fraudulent_transaction(self, amount: float) -> bool:
        """Returns True if transaction amount deviates suspiciously from normal baseline."""
        prediction = self.fraud_detector.predict(np.array([[amount]]))
        return True if prediction[0] == -1 else False

    def segment_customers(self, customer_data: List[List[float]]) -> List[str]:
        """Classifies customers into Premium, Regular, or Budget tiers using K-Means."""
        if not customer_data or len(customer_data) < 3:
            return ["REGULAR"] * len(customer_data)
        
        kmeans = KMeans(n_clusters=3, random_state=42).fit(customer_data)
        labels = kmeans.labels_
        mapping = {0: "PREMIUM", 1: "REGULAR", 2: "BUDGET"}
        return [mapping[lbl] for lbl in labels]