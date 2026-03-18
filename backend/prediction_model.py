"""
prediction_model.py — ML Risk Prediction
==========================================
This module loads the pre-trained Random Forest model
and uses it to predict whether a student is at risk
of falling below the required attendance.

The model was trained in ml/train_model.py.
"""

import pickle
import os
import numpy as np
import pandas as pd

# -- Path to the saved model ===============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ml", "model.pkl")

# --- Load model once at module import (not on every request)=============
_model_data = None

def _load_model():
    """Load the model from disk. Called once and cached."""
    global _model_data
    if _model_data is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found at {MODEL_PATH}. "
                "Please run: python ml/train_model.py"
            )
        with open(MODEL_PATH, "rb") as f:
            _model_data = pickle.load(f)
    return _model_data


def predict_risk(
    attendance_percentage: float,
    recent_absences: int,
    total_classes: int,
    attendance_trend: float,
) -> dict:
    """
    Predict whether a student is at risk of falling below
    the required attendance threshold.

    Args:
        attendance_percentage : current attendance % (e.g., 72.5)
        recent_absences       : absences in the last 10 classes
        total_classes         : total classes conducted so far
        attendance_trend      : positive = improving, negative = declining

    Returns:
        {
            "risk_probability": 0.87,    # 0.0 to 1.0
            "risk_level": "HIGH",        # LOW / MEDIUM / HIGH
            "at_risk": True,             # boolean
            "message": "..."             # human-readable explanation
        }
    """
    model_data = _load_model()
    model = model_data["model"]

    # Build the feature vector using a DataFrame so feature names match training
    features = pd.DataFrame([{
        "attendance_percentage": attendance_percentage,
        "recent_absences":       recent_absences,
        "total_classes":         total_classes,
        "attendance_trend":      attendance_trend,
    }])

    # Get prediction and probability
    prediction = model.predict(features)[0]           # 0 or 1
    probabilities = model.predict_proba(features)[0]  # [prob_0, prob_1]
    risk_probability = round(float(probabilities[1]), 4)  # probability of being at risk

    # Map probability to risk level
    if risk_probability < 0.35:
        risk_level = "LOW"
        message = (
            f"Your attendance looks healthy at {attendance_percentage:.1f}%. "
            "Keep it up!"
        )
    elif risk_probability < 0.65:
        risk_level = "MEDIUM"
        message = (
            f"Your attendance is at {attendance_percentage:.1f}% — "
            "you're in a cautious zone. Try not to miss more classes."
        )
    else:
        risk_level = "HIGH"
        message = (
            f"⚠️ HIGH RISK! Your attendance is at {attendance_percentage:.1f}%. "
            "You need to attend more classes immediately."
        )

    return {
        "risk_probability": risk_probability,
        "risk_level": risk_level,
        "at_risk": bool(prediction == 1),
        "message": message,
        "model_type": model_data.get("model_type", "Unknown"),
    }
