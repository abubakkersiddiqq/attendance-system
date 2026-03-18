#  AI Based Student Attendance Prediction & Notification System
### Final Year  BCA Project | Python · FastAPI · scikit-learn · Telegram · React

---

## Table of Contents
1. [System Architecture](#1-system-architecture)
2. [Project Folder Structure](#2-project-folder-structure)
3. [Data Structure Design](#3-data-structure-design)
4. [How the Math Works](#4-how-the-math-works)
5. [How the ML Model Works](#5-how-the-ml-model-works)
6. [Step-by-Step Setup](#6-step-by-step-setup)
7. [Running the Backend API](#7-running-the-backend-api)
8. [Training the ML Model](#8-training-the-ml-model)
9. [Running the Telegram Bot](#9-running-the-telegram-bot)
10. [Running the React Dashboard](#10-running-the-react-dashboard)
11. [API Reference](#11-api-reference)
12. [Deployment Guide](#12-deployment-guide)
13. [Demo Script for Presentation](#13-demo-script-for-presentation)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Attendance System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Student          Telegram Bot          React Dashboard        │
│   (User)  ──────▶  (bot_handler.py) ◀── (Vercel)               │
│                         │                    │                  │
│                         ▼                    ▼                  │
│                  ┌──────────────────────────────┐               │
│                  │   FastAPI Backend (Render)   │               │
│                  │   main.py                    │               │
│                  │       │                      │               │
│                  │  ┌────┴────────────────────┐ │               │
│                  │  │  attendance_engine.py   │ │               │
│                  │  │  (Math calculations)    │ │               │
│                  │  └─────────────────────────┘ │               │
│                  │  ┌─────────────────────────┐ │               │
│                  │  │  prediction_model.py    │ │               │
│                  │  │  (ML predictions)       │ │               │
│                  │  └─────────────────────────┘ │               │
│                  │  ┌─────────────────────────┐ │               │
│                  │  │  storage.py             │ │               │
│                  │  │  (JSON + CSV files)     │ │               │
│                  │  └─────────────────────────┘ │               │
│                  └──────────────────────────────┘               │
│                                                                 │
│   Data Files:  data/students.json                               │
│                data/attendance.csv                              │
│   ML Files:    ml/model.pkl (trained model)                     │
│                ml/dataset.csv (training data)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | File | What it does |
|---|---|---|
| FastAPI Backend | `backend/main.py` | Hosts all API endpoints, connects everything |
| Attendance Engine | `backend/attendance_engine.py` | Math calculations (%, safe bunks) |
| ML Predictor | `backend/prediction_model.py` | Loads model, returns risk level |
| Storage | `backend/storage.py` | Read/write JSON and CSV files |
| Telegram Bot | `backend/bot_handler.py` | Chatbot interface for students |
| ML Training | `ml/train_model.py` | Trains and saves the Random Forest model |
| React Dashboard | `frontend/src/App.jsx` | Web UI showing all data |

---

## 2. Project Folder Structure

```
attendance-project/
│
├── backend/                    ← FastAPI backend (Python)
│   ├── main.py                 ← API routes and app entry point
│   ├── attendance_engine.py    ← Math: percentage, safe bunks
│   ├── prediction_model.py     ← Loads ML model, predicts risk
│   ├── storage.py              ← Read/write JSON and CSV files
│   ├── bot_handler.py          ← Telegram bot
│   └── requirements.txt        ← Python dependencies
│
├── ml/                         ← Machine Learning
│   ├── train_model.py          ← Training script
│   ├── dataset.csv             ← Training data (100 students)
│   └── model.pkl               ← Saved trained model (auto-generated)
│
├── frontend/                   ← React dashboard
│   ├── src/
│   │   ├── App.jsx             ← Main dashboard component
│   │   ├── index.css           ← Styles
│   │   └── main.jsx            ← React entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── data/                       ← Data storage (no database needed)
│   ├── students.json           ← Student profiles
│   └── attendance.csv          ← Attendance records
│
├── render.yaml                 ← Render deployment config
└── README.md                   ← This file
```

---

## 3. Data Structure Design

### students.json
Stores student profiles as a key-value object where the key is the student ID.

```json
{
  "CS2021001": {
    "student_id": "U19MT23S0040",
    "name": "Arjun Sharma",
    "required_percentage": 75.0,
    "created_at": "2026-01-10T09:00:00"
  }
}
```

### attendance.csv
Stores every attendance event as a row. Each row also stores the running totals so we can quickly look up the latest state.

```
student_id, date,       status,  subject,     total_classes, classes_attended
CS2021001,  2026-01-15, present, Mathematics, 1,             1
CS2021002,  2026-01-16, present, Physics,     2,             2
CS2021003,  2026-01-17, absent,  Chemistry,   3,             2
```

**Why CSV and not a database?**
For a college project that needs to run on free hosting, CSV files are perfect:
- No setup required
- No installation
- Easy to inspect and debug
- Works on any machine

---

## 4. How the Math Works

### Attendance Percentage
```
attendance_percentage = (classes_attended / total_classes) × 100
```
Example: 30 attended out of 40 total → (30/40) × 100 = **75%**

### Safe Bunk Calculation

**Question:** How many more classes can I skip while staying above 75%?

**Define:**
- P = classes attended (present)
- T = total classes conducted
- R = required fraction (0.75 for 75%)
- x = number of future classes to skip

**Constraint:** After skipping x classes, attendance must still be ≥ R:
```
P / (T + x) ≥ R
```

**Solve for x:**
```
P ≥ R × (T + x)
P ≥ R×T + R×x
P - R×T ≥ R×x
x ≤ (P - R×T) / R

∴  safe_bunks = floor( (P - R×T) / R )
```

**Example:**
```
P = 30,  T = 36,  R = 0.75
safe_bunks = floor( (30 - 0.75 × 36) / 0.75 )
           = floor( (30 - 27) / 0.75 )
           = floor( 3 / 0.75 )
           = floor( 4.0 )
           = 4
```
The student can skip **4 more classes** and still be at exactly 75%.

---

## 5. How the ML Model Works

### What it predicts
The model predicts whether a student will fall below 75% attendance (binary classification: at_risk = 0 or 1).

### Features (inputs to the model)

| Feature | Description | Example |
|---|---|---|
| `attendance_percentage` | Current attendance % | 72.5 |
| `recent_absences` | Absences in last 10 classes | 4 |
| `total_classes` | Total classes conducted | 40 |
| `attendance_trend` | Is attendance improving? (+ve) or declining? (-ve) | -2 |

### Algorithm: Random Forest Classifier
A Random Forest builds many decision trees and takes a majority vote. It's great because:
- Works well on small datasets
- Handles non-linear patterns
- Doesn't need feature scaling
- Gives probability scores (not just yes/no)

### Risk Levels

| Probability | Risk Level | Meaning |
|---|---|---|
| 0% – 34% | 🟢 LOW | Student is safe |
| 35% – 64% | 🟡 MEDIUM | Student should be careful |
| 65% – 100% | 🔴 HIGH | Immediate action needed |

---
## Authors
GOAT Attendance System — Final Year Project 2026
