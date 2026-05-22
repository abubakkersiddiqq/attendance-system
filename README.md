# AI Based Student Attendance Prediction and Notification System

Final Year BCA Project | Python, FastAPI, scikit-learn, React, Telegram

---

## Live Demo

| Service            | URL                                              |
| ------------------ | ------------------------------------------------ |
| Backend API        | https://attendance-system-eev2.onrender.com      |
| API Docs (Swagger) | https://attendance-system-eev2.onrender.com/docs |
| Frontend Dashboard | https://attendance-system-kohl-nine.vercel.app/  |
| Telegram Bot       | @AttendIQBot                                     |

---

## Project Overview

A full-stack AI system that helps college students track their subject-wise attendance, calculate how many classes they can safely miss, and predict if they are at risk of falling below the required attendance percentage.

Students interact through a **Telegram bot** or a **React web dashboard**.

---

## Features

- Subject-wise attendance tracking per student
- Safe bunk calculator using mathematical formula
- ML risk prediction — Random Forest Classifier (100% accuracy on test set)
- Telegram bot with natural language understanding and slash commands
- React web dashboard with real-time attendance cards and trend charts
- MongoDB Atlas for persistent cloud storage
- LLM-powered personalised advice via OpenRouter API
- College roll number validation (format: `U19MT23S0054`)

---

## Tech Stack

| Layer        | Technology                                |
| ------------ | ----------------------------------------- |
| Backend API  | Python 3.12, FastAPI                      |
| Database     | MongoDB Atlas (pymongo)                   |
| ML Model     | scikit-learn — Random Forest Classifier   |
| Frontend     | React 18, Vite                            |
| Telegram Bot | python-telegram-bot v21                   |
| LLM          | OpenRouter API (`openrouter/free`)        |
| Deployment   | Render (backend + bot), Vercel (frontend) |

---

## Project Structure

```
attendance-system/
│
├── backend/
│   ├── main.py                 API routes
│   ├── attendance_engine.py    Safe bunk math
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
│   ├── dataset.csv             Training data (100 records)
│   └── model.pkl               Trained model
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
└── runtime.txt                 Python 3.12.9 (for Render)
```

---

## Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/abubakkersiddiqq/attendance-system.git
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

### 4. Create `backend/.env`

```
TELEGRAM_BOT_TOKEN=your_token_here
BACKEND_URL=http://localhost:8000
MONGODB_URI=your_mongodb_atlas_connection_string
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=openrouter/free
```

### 5. Train the ML model

```bash
cd ml
python train_model.py
cd ..
```

### 6. Run backend + bot + frontend (3 terminals)

```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 - Bot (use mobile hotspot if on college WiFi)
cd backend
python bot_handler.py

# Terminal 3 - Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## ML Model

- Algorithm: Random Forest Classifier
- Training data: 100 synthetic student records
- Train/test split: 80/20
- Test accuracy: 100%
- Input features: attendance percentage, recent absences, total classes, attendance trend
- Output: `at_risk` / `safe`

---

## Bot Commands

| Command                | Description                        |
| ---------------------- | ---------------------------------- |
| `/start`               | Start the bot                      |
| `/help`                | Show all commands                  |
| `/register`            | Create your profile (guided steps) |
| `/link`                | Link your roll number              |
| `/present SubjectName` | Mark present                       |
| `/absent SubjectName`  | Mark absent                        |
| `/attendance`          | Overall attendance percentage      |
| `/subject SubjectName` | One subject attendance             |
| `/subjects`            | List all subjects                  |
| `/bunk`                | Safe bunks overall                 |
| `/predict`             | ML risk prediction                 |
| `/report`              | Full report with all subjects      |
| `/advice`              | Personalised AI advice             |
| `/plan`                | Today's plan                       |
| `/history`             | All attendance records             |
| `/addsubject`          | Add a subject (Settings only)      |
| `/removesubject`       | Remove a subject (Settings only)   |

💬 Natural language also supported — _"Can I bunk PHP today?"_, _"Mark me present in Python"_

---

## Deployment

- Backend deployed on **Render** (free tier) with start command running uvicorn and bot together
- Frontend deployed on **Vercel**
- Database on **MongoDB Atlas** (free M0 cluster)
- Uptime maintained via **UptimeRobot** (pings `/health` every 5 minutes)

---

## Team

| Name               | Roll Number  |
| ------------------ | ------------ |
| S Abubakker Siddiq | U19MT23S0054 |
| Raghul Muniraj     | U19MT23S0042 |
| Prajwal V          | U19MT23S0040 |

**Guide:** Mrs. Nafisa S, Associate Professor, Department of Computer Science
