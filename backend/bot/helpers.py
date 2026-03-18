"""
bot/helpers.py
==============
Shared utilities used across all bot modules:
  - API GET/POST helpers
  - Intent detection (LLM + keyword fallback)
  - Subject extraction
  - Emoji helpers
  - Guard: _require_sid
"""

import os
import re
import math
import requests
from difflib import get_close_matches
from telegram import Update
import llm_service

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

# In-memory map: telegram user_id -> student roll number
USER_MAP: dict = {}


# ── API helpers ───────────────────────────────────────────────────────────────

def GET(path: str) -> dict:
    try:
        r = requests.get(f"{BACKEND}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        try:    return {"error": e.response.json().get("detail", str(e))}
        except: return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def POST(path: str, body: dict) -> dict:
    try:
        r = requests.post(f"{BACKEND}{path}", json=body, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        try:    return {"error": e.response.json().get("detail", str(e))}
        except: return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


# ── Intent detection ──────────────────────────────────────────────────────────

KEYWORD_INTENTS = {
    "attendance":     ["attendance", "percentage", "how many", "what is my", "classes"],
    "bunk":           ["bunk", "skip", "miss", "can i", "safe", "should i skip"],
    "predict":        ["risk", "predict", "danger", "below", "fall", "at risk", "will i fail"],
    "report":         ["report", "summary", "full", "complete", "show all", "everything"],
    "mark_present":   ["mark present", "i came", "attended today", "present today", "i attended"],
    "mark_absent":    ["mark absent", "i missed", "absent today", "did not attend", "skipped today"],
    "subjects":       ["subjects", "subject list", "my subjects", "show subjects", "list subjects"],
    "add_subject":    ["add subject", "new subject", "addsubject", "add class"],
    "remove_subject": ["remove subject", "delete subject", "drop subject"],
    "history":        ["history", "past", "records", "log", "previous"],
    "advice":         ["advice", "suggest", "recommend", "what should i", "help me"],
    "plan":           ["plan", "today", "what to do", "should i attend"],
    "help":           ["help", "commands", "what can", "options", "menu"],
    "register":       ["register", "signup", "create", "new student"],
    "link":           ["link", "connect", "my id"],
}


def detect_intent(text: str, student_id: str = None) -> dict:
    """
    Returns {"intent": str, "subject": str|None}.
    Tries LLM first, then keyword matching, then fuzzy matching.
    """
    # 1. Try LLM
    llm_result = llm_service.detect_intent_llm(text)
    if llm_result and "intent" in llm_result:
        return llm_result

    # 2. Keyword match
    t = text.lower().strip()
    matched = "unknown"
    for intent, kws in KEYWORD_INTENTS.items():
        for kw in kws:
            if kw in t:
                matched = intent
                break
        if matched != "unknown":
            break

    # 3. Fuzzy match fallback
    if matched == "unknown":
        all_kw = {kw: intent for intent, kws in KEYWORD_INTENTS.items() for kw in kws}
        for word in t.split():
            m = get_close_matches(word, all_kw.keys(), n=1, cutoff=0.78)
            if m:
                matched = all_kw[m[0]]
                break

    return {"intent": matched, "subject": extract_subject(text, student_id)}


def extract_subject(text: str, student_id: str = None) -> str | None:
    """Extract subject name from message, matching against registered subjects."""
    t = text.strip()

    if student_id:
        data = GET(f"/subjects/{student_id}")
        if "error" not in data:
            registered = data.get("subjects", [])
            t_lower = t.lower()
            # Exact match
            for subj in registered:
                if subj.lower() in t_lower:
                    return subj
            # Fuzzy match
            reg_lower = {s.lower(): s for s in registered}
            for word in t.split():
                m = get_close_matches(word.lower(), reg_lower.keys(), n=1, cutoff=0.75)
                if m:
                    return reg_lower[m[0]]

    # Regex fallback
    patterns = [
        r"(?:bunk|skip|miss|attend|present in|absent in|for|in|of)\s+([A-Za-z][A-Za-z\s]{1,25}?)(?:\s+class|\s+today|$|\?|\.)",
        r"my\s+([A-Za-z][A-Za-z\s]{1,25}?)\s+(?:attendance|%|percentage)",
        r"add\s+([A-Za-z][A-Za-z\s]{1,25}?)\s+(?:to my subjects|subject|class)",
        r"remove\s+([A-Za-z][A-Za-z\s]{1,25}?)\s+(?:from|subject)",
    ]
    for pat in patterns:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            return m.group(1).strip().title()
    return None


# ── Emoji helpers ─────────────────────────────────────────────────────────────

def risk_emoji(level: str) -> str:
    return {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(level, "⚪")


def pct_emoji(p: float) -> str:
    return "✅" if p >= 75 else ("⚠️" if p >= 65 else "🔴")


def safe_bunks_calc(attended: int, total: int, req: float = 0.75) -> int:
    if total == 0:
        return 0
    return max(0, math.floor((attended - req * total) / req))


# ── Guard ─────────────────────────────────────────────────────────────────────

async def require_sid(update: Update) -> str | None:
    """Return the student ID for this Telegram user, or send an error and return None."""
    sid = USER_MAP.get(update.effective_user.id)
    if not sid:
        await update.message.reply_text(
            "🔗 You are not linked to a student profile yet.\n\n"
            "Use /register to create a new profile, or\n"
            "/link ROLLNUMBER if you already have one.",
            parse_mode="Markdown",
        )
    return sid
