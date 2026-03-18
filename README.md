# AI Based Student Attendance Prediction and Notification System

Final Year BCA Project | Python, FastAPI, scikit-learn, React, Telegram

---

## Project Overview

A full-stack AI system that helps college students track their subject-wise attendance, calculate how many classes they can safely miss, and predict if they are at risk of falling below the required attendance percentage.

Students interact through a Telegram bot or a React web dashboard.

---

## Features

- Subject-wise attendance tracking
- Safe bunk calculator using mathematical formula
- Machine learning risk prediction (Random Forest)
- Telegram chatbot with natural language support
- React web dashboard with attendance charts
- MongoDB Atlas for persistent cloud storage
- College roll number validation (format: U19MT23S0054)
- LLM-powered advice via OpenRouter (optional)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Database | MongoDB Atlas |
| ML Model | scikit-learn (Random Forest) |
| Frontend | React 18, Vite |
| Telegram Bot | python-telegram-bot |
| LLM (optional) | OpenRouter API |
| Deployment | Render (backend), Vercel (frontend) |

---

## Project Structure

```
attendance-system/
│
├── backend/
│   ├── main.py                 API routes
│   ├── attendance_engine.py    Math calculations
│   ├── prediction_model.py     ML predictions
│   ├── storage.py              MongoDB database layer
│   ├── llm_service.py          OpenRouter LLM integration
│   ├── bot_handler.py          Telegram bot entry point
│   ├── bot/
│   │   ├── helpers.py          API calls, intent detection
│   │   ├── registration.py     /register conversation
│   │   ├── commands.py         All slash commands
│   │   └── natural_language.py Free-text message handler
│   └── requirements.txt
│
├── ml/
│   ├── train_model.py          Model training script
│   ├── dataset.csv             Training data
│   └── model.pkl               Trained model (generated)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
└── data/                       Local data (not pushed to GitHub)
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/attendance-system.git
cd attendance-system
```

### 2. Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Create backend/.env

```
TELEGRAM_BOT_TOKEN=your_token_here
BACKEND_URL=http://localhost:8000
MONGODB_URI=your_mongodb_atlas_connection_string
OPENROUTER_API_KEY=your_key_here
```

### 5. Train the ML model

```bash
cd ml
python train_model.py
cd ..
```

### 6. Run the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 7. Run the Telegram bot (separate terminal)

```bash
cd backend
python bot_handler.py
```

### 8. Run the frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Team

| Name | Roll Number |
|---|---|
| S Abubakker Siddiq | U19MT23S0054 |
| Raghul Muniraj | U19MT23S0042 |
| Prajwal V | U19MT23S0040 |

**Guide:** Mrs. Nafisa S, Associate Professor, Department of Computer Science

---

## Status

Work in progress — MongoDB Atlas integration in progress.
