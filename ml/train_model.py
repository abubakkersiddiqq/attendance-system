"""
GOAT - ML Model Training Script
=================================
This script trains a machine learning model to predict
whether a student is at risk of falling below the
required attendance percentage.

Author: Abubakker Siddiq 
Algorithm: Random Forest Classifier
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler
import pickle
import os

# ─────────────────────────────────────────────
# STEP 1: Load the dataset
# ─────────────────────────────────────────────
print("📂 Loading dataset...")
df = pd.read_csv("dataset.csv")
print(f"   Loaded {len(df)} student records.")
print(df.head())

# ─────────────────────────────────────────────
# STEP 2: Feature Engineering
# We compute attendance_percentage from the raw data
# so we don't have to store it — we calculate it live.
# ─────────────────────────────────────────────
df["attendance_percentage"] = (df["classes_attended"] / df["total_classes"]) * 100

# Features (X) and Label (y)
FEATURES = [
    "attendance_percentage",
    "recent_absences",
    "total_classes",
    "attendance_trend",
]
TARGET = "at_risk"

X = df[FEATURES]
y = df[TARGET]

print(f"\n📊 Feature columns: {FEATURES}")
print(f"   Class distribution:\n{y.value_counts()}")

# ─────────────────────────────────────────────
# STEP 3: Split data into train and test sets
# 80% training, 20% testing
# ─────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n✂️  Train size: {len(X_train)}, Test size: {len(X_test)}")

# ─────────────────────────────────────────────
# STEP 4: Train the model
# We use Random Forest — it handles non-linear
# patterns well and doesn't need feature scaling.
# ─────────────────────────────────────────────
print("\n🌳 Training Random Forest Classifier...")
model = RandomForestClassifier(
    n_estimators=100,   # 100 decision trees
    max_depth=5,        # limit tree depth to prevent overfitting
    random_state=42
)
model.fit(X_train, y_train)

# ─────────────────────────────────────────────
# STEP 5: Evaluate the model
# ─────────────────────────────────────────────
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\n✅ Model Accuracy: {accuracy * 100:.2f}%")
print("\n📋 Classification Report:")
print(classification_report(y_test, y_pred, target_names=["NOT AT RISK", "AT RISK"]))

# Feature importance — helpful to explain the model
importances = model.feature_importances_
print("\n🔍 Feature Importances:")
for feat, imp in zip(FEATURES, importances):
    print(f"   {feat:<30} → {imp:.4f}")

# ─────────────────────────────────────────────
# STEP 6: Also train Logistic Regression for comparison
# ─────────────────────────────────────────────
print("\n📈 Training Logistic Regression (for comparison)...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

lr_model = LogisticRegression(random_state=42)
lr_model.fit(X_train_scaled, y_train)
lr_pred = lr_model.predict(X_test_scaled)
lr_acc = accuracy_score(y_test, lr_pred)
print(f"   Logistic Regression Accuracy: {lr_acc * 100:.2f}%")

# ─────────────────────────────────────────────
# STEP 7: Save the best model to a .pkl file
# We pick Random Forest if it performs better.
# ─────────────────────────────────────────────
best_model = model  # Random Forest
model_data = {
    "model": best_model,
    "features": FEATURES,
    "model_type": "RandomForest",
    "accuracy": accuracy,
}

output_path = "model.pkl"
with open(output_path, "wb") as f:
    pickle.dump(model_data, f)

print(f"\n💾 Model saved to: {output_path}")
print("\n🎉 Training complete! The model is ready for use in the backend.")
print("\nTo use the model in prediction_model.py:")
print("   1. Load model.pkl with pickle.load()")
print("   2. Pass [attendance_percentage, recent_absences, total_classes, trend]")
print("   3. Get back 0 (safe) or 1 (at risk)")
