"""
llm_service.py — OpenRouter LLM Integration
=============================================
Set OPENROUTER_API_KEY in your .env to enable.
If the key is missing, all functions fall back gracefully
to the rule-based system — nothing breaks.

Model: mistralai/mistral-7b-instruct:free 
"""

import os, json, requests
from typing import Optional

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL          = os.getenv("LLM_MODEL", "mistralai/mistral-7b-instruct:free")
LLM_ENABLED        = bool(OPENROUTER_API_KEY)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _call_llm(system_prompt: str, user_message: str,
              max_tokens: int = 300) -> Optional[str]:
    """
    Low-level call to OpenRouter.
    Returns the model's reply string, or None on failure.
    """
    if not LLM_ENABLED:
        return None
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://goat-attendance.app",
                "X-Title":       "GOAT Attendance System",
            },
            json={
                "model": LLM_MODEL,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system",  "content": system_prompt},
                    {"role": "user",    "content": user_message},
                ],
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return None


# ── Intent Detection ──────────────────────────────────────────────────────────

INTENT_SYSTEM = """You are an intent classifier for a student attendance bot.
Given the user's message, return a JSON object with exactly two fields:
  "intent": one of [attendance, bunk, predict, report, subjects, history,
                    mark_present, mark_absent, add_subject, remove_subject,
                    help, register, link, unknown]
  "subject": the subject name if mentioned, otherwise null

Rules:
- "bunk" means the user wants to know if they can skip a class
- "mark_present" / "mark_absent" means recording today's attendance
- "attendance" means checking current percentage
- "add_subject" means adding a new subject to their list
- Return ONLY valid JSON, no explanation, no markdown.

Examples:
  "can I bunk physics today?"         → {"intent":"bunk","subject":"Physics"}
  "mark me present in machine learning" → {"intent":"mark_present","subject":"Machine Learning"}
  "what is my math attendance?"       → {"intent":"attendance","subject":"Math"}
  "add data structures to my subjects" → {"intent":"add_subject","subject":"Data Structures"}
  "am i at risk?"                     → {"intent":"predict","subject":null}
  "show all my subjects"              → {"intent":"subjects","subject":null}
"""

def detect_intent_llm(message: str) -> Optional[dict]:
    """
    Use LLM to detect intent and extract subject.
    Returns {"intent": str, "subject": str|None} or None if LLM unavailable.
    """
    reply = _call_llm(INTENT_SYSTEM, message, max_tokens=60)
    if not reply:
        return None
    try:
        # Strip markdown fences if model added them
        clean = reply.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except Exception:
        return None


# ── Smart Advice ──────────────────────────────────────────────────────────────

ADVICE_SYSTEM = """You are a friendly academic advisor for a college student.
You have the student's attendance data. Give short, practical advice (2-4 sentences).
Be encouraging but honest. Focus on actionable next steps.
Do NOT repeat numbers back to the student — they already know them.
Do NOT use bullet points. Write naturally."""

def get_smart_advice(student_name: str, report: dict) -> str:
    """
    Generate personalised advice based on the student's attendance report.
    Falls back to a rule-based message if LLM is unavailable.
    """
    if not LLM_ENABLED:
        return _rule_based_advice(report)

    # Build a compact summary for the LLM
    subjects = report.get("subjects", [])
    weak     = [s for s in subjects if s["attendance_percentage"] < 75]
    strong   = [s for s in subjects if s["attendance_percentage"] >= 85]

    context = (
        f"Student: {student_name}\n"
        f"Overall attendance: {report.get('attendance_percentage', 0):.1f}%\n"
        f"Safe bunks remaining: {report.get('safe_bunks', 0)}\n"
        f"ML risk level: {report.get('ml_prediction', {}).get('risk_level', 'UNKNOWN')}\n"
        f"Subjects below 75%: {[s['subject'] for s in weak]}\n"
        f"Strong subjects (>85%): {[s['subject'] for s in strong]}\n"
        f"Classes needed to recover: {report.get('classes_needed_to_recover', 0)}"
    )

    reply = _call_llm(
        ADVICE_SYSTEM,
        f"Give advice to this student:\n{context}",
        max_tokens=150,
    )
    return reply or _rule_based_advice(report)


def _rule_based_advice(report: dict) -> str:
    """Fallback advice when LLM is not configured."""
    pct      = report.get("attendance_percentage", 0)
    risk     = report.get("ml_prediction", {}).get("risk_level", "LOW")
    weak     = [s["subject"] for s in report.get("subjects", [])
                if s["attendance_percentage"] < 75]
    recovery = report.get("classes_needed_to_recover", 0)

    if risk == "HIGH" or pct < 65:
        msg = f"Your attendance is critically low at {pct:.1f}%. "
        if recovery > 0:
            msg += f"You need to attend {recovery} consecutive classes to recover. "
        if weak:
            msg += f"Focus especially on: {', '.join(weak)}."
        return msg
    elif risk == "MEDIUM" or pct < 75:
        msg = f"You're close to the 75% threshold. Avoid skipping any more classes. "
        if weak:
            msg += f"Subjects needing attention: {', '.join(weak)}."
        return msg
    else:
        bunks = report.get("safe_bunks", 0)
        return (f"You're doing well at {pct:.1f}%! "
                f"You can safely skip up to {bunks} more class(es). "
                f"Keep attending regularly to maintain this.")


# ── Today's Plan ──────────────────────────────────────────────────────────────

PLAN_SYSTEM = """You are a helpful academic assistant. 
Based on the student's attendance data, tell them what they should do today.
Be direct and friendly. 2-3 sentences maximum. No bullet points."""

def get_today_plan(student_name: str, report: dict) -> str:
    """Answer: 'What should I do today?'"""
    if not LLM_ENABLED:
        return _rule_based_plan(report)

    subjects = report.get("subjects", [])
    urgent   = [s for s in subjects if s["attendance_percentage"] < 75]
    ok       = [s for s in subjects if s["attendance_percentage"] >= 75]

    context = (
        f"Student: {student_name}\n"
        f"Overall: {report.get('attendance_percentage',0):.1f}%\n"
        f"Subjects BELOW 75% (must attend): {[s['subject'] for s in urgent]}\n"
        f"Subjects OK: {[s['subject'] for s in ok]}\n"
        f"Safe bunks overall: {report.get('safe_bunks', 0)}"
    )
    reply = _call_llm(PLAN_SYSTEM, f"What should this student do today?\n{context}",
                      max_tokens=100)
    return reply or _rule_based_plan(report)


def _rule_based_plan(report: dict) -> str:
    urgent = [s["subject"] for s in report.get("subjects", [])
              if s["attendance_percentage"] < 75]
    bunks  = report.get("safe_bunks", 0)
    if urgent:
        return (f"You MUST attend today — especially {', '.join(urgent[:2])}. "
                f"Your attendance in these subjects is below 75%.")
    elif bunks > 0:
        return (f"You have {bunks} safe bunk(s) available overall. "
                f"Still, attending today will give you more flexibility later.")
    else:
        return "Attend all your classes today — you have no safe bunks remaining."


# ── Status ────────────────────────────────────────────────────────────────────

def llm_status() -> dict:
    return {
        "enabled":    LLM_ENABLED,
        "model":      LLM_MODEL if LLM_ENABLED else "Not configured",
        "message":    ("LLM active" if LLM_ENABLED
                       else "Set OPENROUTER_API_KEY in .env to enable LLM features"),
    }
