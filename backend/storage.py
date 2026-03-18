"""
storage.py — Data Storage Layer (v2 — subject-aware)
======================================================
Data files:
  data/students.json    → student profiles + their subjects list
  data/attendance.csv   → every attendance event (per subject)


storage.py v3.1
===============
Validation added:
  - validate_student_id : letters+digits, 4-20 chars, both required
  - validate_name       : letters and spaces only, 2-60 chars
  - validate_subjects   : min 1, max 15, no duplicates, no symbols
  - create_student      : blocks duplicate roll numbers with clear error
"""

import json, csv, os, re
from datetime import datetime
from typing import Optional

BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR        = os.path.join(BASE_DIR, "data")
STUDENTS_FILE   = os.path.join(DATA_DIR, "students.json")
ATTENDANCE_FILE = os.path.join(DATA_DIR, "attendance.csv")
os.makedirs(DATA_DIR, exist_ok=True)

FIELDS = ["student_id","date","status","subject","total_classes","classes_attended"]


# -====================== Validation =======================

def parse_college_roll_number(sid: str) -> dict:
    """
    Parse a roll number in college format: U19MT23S0054
      U     = University prefix (1 letter)
      19MT  = College code (2-digit year + 2-4 letters)
      23    = Batch/joining year (2 digits)
      S0054 = Serial number (1 letter + 3-6 digits)

    Returns a dict with parsed parts, or empty dict if format does not match.
    """
    sid = sid.strip().upper()
    m = re.match(
        r'^([A-Z])([0-9]{2}[A-Z]{2,4})([0-9]{2})([A-Z][0-9]{3,6})$',
        sid
    )
    if not m:
        return {}
    batch_year = int(m.group(3))
    full_year  = 2000 + batch_year
    return {
        "university_prefix": m.group(1),          # U
        "college_code":      m.group(2),           # 19MT
        "batch_year":        f"{full_year}",       # 2023
        "serial":            m.group(4),           # S0054
        "formatted":         (
            f"University: {m.group(1)} | "
            f"College: {m.group(2)} | "
            f"Batch: {full_year} | "
            f"Serial: {m.group(4)}"
        )
    }


def validate_student_id(sid: str) -> tuple:
    """
    Roll number rules:
      - 4 to 20 characters, letters and digits only (no spaces, no symbols)
      - Must contain at least one letter AND at least one digit
      - Preferred format: U19MT23S0054
          U     = University prefix
          19MT  = College code (year + dept)
          23    = Batch year
          S0054 = Serial number

    Returns (True, normalised_sid) or (False, error_message).
    """
    sid = sid.strip().upper()

    # Basic character and length check
    if not re.match(r'^[A-Z0-9]{4,20}$', sid):
        return False, (
            "Roll number must be 4-20 characters, letters and digits only.\n"
            "Example: U19MT23S0054"
        )

    has_letter = bool(re.search(r'[A-Z]', sid))
    has_digit  = bool(re.search(r'[0-9]', sid))

    if not has_letter:
        return False, "Roll number must contain at least one letter. Example: U19MT23S0054"
    if not has_digit:
        return False, "Roll number must contain at least one digit. Example: U19MT23S0054"

    return True, sid


def validate_name(name: str) -> tuple:
    """
    Name rules:
      - 2 to 60 characters
      - Letters and spaces only (no digits, no symbols)
    Examples: Arjun Sharma, Priya Nair
    """
    name = name.strip()
    if not name:
        return False, "Name cannot be empty."
    if len(name) < 2:
        return False, "Name must be at least 2 characters."
    if len(name) > 60:
        return False, "Name must be 60 characters or less."
    if not re.match(r'^[A-Za-z ]+$', name):
        return False, "Name must contain letters and spaces only — no numbers or symbols."
    return True, name


def validate_subjects(raw_subjects: list) -> tuple:
    """
    Subject rules:
      - Minimum 1, maximum 15
      - Each subject: 2-50 characters, letters/digits/spaces only
      - No duplicate names (case-insensitive)
      - Empty entries are silently dropped
    Returns (ok, cleaned_list, error_message).
    """
    cleaned = [s.strip().title() for s in raw_subjects if s.strip()]

    if len(cleaned) == 0:
        return False, [], "Please add at least one subject."
    if len(cleaned) > 15:
        return False, [], f"Maximum 15 subjects allowed. You entered {len(cleaned)}."

    for s in cleaned:
        if len(s) < 2:
            return False, [], f"Subject '{s}' is too short (minimum 2 characters)."
        if len(s) > 50:
            return False, [], f"Subject '{s}' is too long (maximum 50 characters)."
        if not re.match(r'^[A-Za-z0-9 ]+$', s):
            return False, [], f"Subject '{s}' contains invalid characters. Use letters, digits and spaces only."

    # Duplicate check (case-insensitive)
    seen = []
    for s in cleaned:
        if s.lower() in [x.lower() for x in seen]:
            return False, [], f"Duplicate subject: '{s}' appears more than once. Please remove the duplicate."
        seen.append(s)

    return True, cleaned, ""


# ====================== Students ====================== 

def _load_students() -> dict:
    if not os.path.exists(STUDENTS_FILE): return {}
    with open(STUDENTS_FILE) as f: return json.load(f)

def _save_students(d: dict):
    with open(STUDENTS_FILE, "w") as f: json.dump(d, f, indent=2)

def get_student(sid: str) -> Optional[dict]:
    return _load_students().get(sid.upper())

def student_exists(sid: str) -> bool:
    return sid.upper() in _load_students()

def create_student(sid: str, name: str,
                   subjects: list,
                   required_percentage: float = 75.0) -> tuple:
    """
    Create a NEW student with full validation.
    Returns (student_dict, error_string).
    error_string is "" on success.

    Validation order:
      1. Roll number format
      2. Roll number uniqueness (blocked if exists)
      3. Name format
      4. Subjects (count, duplicates, characters)
    """
    # 1 Validate roll number format
    ok, result = validate_student_id(sid)
    if not ok:
        return {}, result
    sid = result  # normalised uppercase

    # 2 Block if roll number already registered
    s = _load_students()
    if sid in s:
        return {}, (
            f"Roll number '{sid}' is already registered under the name '{s[sid]['name']}'. "
            f"Each student can only register once. If this is you, use /link {sid} to connect."
        )

    # 3 Validate name
    ok, name = validate_name(name)
    if not ok:
        return {}, name  # name holds the error string here

    # 4 Validate subjects
    ok, cleaned_subjects, err = validate_subjects(subjects)
    if not ok:
        return {}, err

    s[sid] = {
        "student_id":          sid,
        "name":                name,
        "required_percentage": required_percentage,
        "subjects":            cleaned_subjects,
        "created_at":          datetime.now().isoformat(),
    }
    _save_students(s)
    return s[sid], ""


def add_subject_to_student(sid: str, subject: str) -> tuple:
    """Add a new subject. Validates name and checks for duplicates."""
    s   = _load_students()
    sid = sid.upper()
    if sid not in s:
        return False, f"Student '{sid}' not found."

    subject = subject.strip().title()
    if not subject:
        return False, "Subject name cannot be empty."
    if len(subject) < 2:
        return False, "Subject name must be at least 2 characters."
    if len(subject) > 50:
        return False, "Subject name must be 50 characters or less."
    if not re.match(r'^[A-Za-z0-9 ]+$', subject):
        return False, "Subject name must contain letters, digits and spaces only."

    existing = s[sid].get("subjects", [])
    if len(existing) >= 15:
        return False, "Maximum 15 subjects allowed. Remove a subject before adding a new one."

    # Duplicate check (case-insensitive)
    if subject.lower() in [x.lower() for x in existing]:
        return False, f"'{subject}' is already in your subjects list."

    existing.append(subject)
    s[sid]["subjects"] = existing
    _save_students(s)
    return True, f"'{subject}' added successfully."


def remove_subject_from_student(sid: str, subject: str) -> tuple:
    """Remove a subject from a student's list."""
    s   = _load_students()
    sid = sid.upper()
    if sid not in s:
        return False, f"Student '{sid}' not found."
    subject = subject.strip().title()
    existing = s[sid].get("subjects", [])
    # Case-insensitive match for removal
    match = next((x for x in existing if x.lower() == subject.lower()), None)
    if not match:
        return False, f"'{subject}' not found in your subjects list."
    existing.remove(match)
    s[sid]["subjects"] = existing
    _save_students(s)
    return True, f"'{match}' removed successfully."


def update_required_percentage(sid: str, pct: float) -> tuple:
    s   = _load_students()
    sid = sid.upper()
    if sid not in s:
        return False, "Student not found."
    if not (50.0 <= pct <= 100.0):
        return False, "Required percentage must be between 50 and 100."
    s[sid]["required_percentage"] = pct
    _save_students(s)
    return True, f"Required attendance updated to {pct}%."

def get_all_students() -> list:
    return list(_load_students().values())


# ================ Attendance ==============

def _load_rows() -> list:
    if not os.path.exists(ATTENDANCE_FILE): return []
    with open(ATTENDANCE_FILE, newline="") as f:
        return list(csv.DictReader(f))

def add_attendance_record(sid: str, status: str, subject: str) -> tuple:
    """
    Add one attendance event.
    Subject is matched case-insensitively against registered subjects.
    If not found, it is auto-added to the student's list.
    """
    sid     = sid.upper()
    subject = subject.strip().title()

    student = get_student(sid)
    if not student:
        return {}, f"Student '{sid}' not found."

    if status not in ("present", "absent"):
        return {}, "Status must be 'present' or 'absent'."

    # Find matching subject (case-insensitive)
    registered = student.get("subjects", [])
    match      = _find_subject(subject, registered)
    if not match:
        # Auto-add subject if not registered
        ok, msg = add_subject_to_student(sid, subject)
        match = subject if ok else subject

    rows = _load_rows()
    sr   = [r for r in rows if r["student_id"]==sid and r["subject"]==match]
    pt   = int(sr[-1]["total_classes"])    if sr else 0
    pa   = int(sr[-1]["classes_attended"]) if sr else 0
    nt   = pt + 1
    na   = pa + (1 if status == "present" else 0)

    rec  = {"student_id": sid, "date": datetime.now().strftime("%Y-%m-%d"),
            "status": status, "subject": match,
            "total_classes": nt, "classes_attended": na}

    exists = os.path.exists(ATTENDANCE_FILE)
    with open(ATTENDANCE_FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists: w.writeheader()
        w.writerow(rec)
    return rec, ""

def _find_subject(query: str, registered: list) -> Optional[str]:
    """Case-insensitive exact match, then partial match."""
    q = query.strip().lower()
    for s in registered:
        if s.lower() == q: return s
    for s in registered:
        if q in s.lower() or s.lower() in q: return s
    return None


# ================== Summaries =================

def get_subject_summary(sid: str, subject: str) -> dict:
    """
    Always returns a summary dict even if there are zero records.
    Subjects show on dashboard immediately after registration.
    """
    sid     = sid.upper()
    subject = subject.strip().title()
    rows    = [r for r in _load_rows()
               if r["student_id"]==sid and r["subject"]==subject]

    if not rows:
        return {
            "student_id": sid, "subject": subject,
            "total_classes": 0, "classes_attended": 0,
            "attendance_percentage": 0.0,
            "recent_absences": 0, "attendance_trend": 0.0,
            "last_updated": "No records yet",
        }

    l     = rows[-1]
    total = int(l["total_classes"]); att = int(l["classes_attended"])
    pct   = round(att/total*100, 2) if total else 0.0
    pr    = lambda sl: sum(1 for r in sl if r["status"]=="present")/len(sl) if sl else 0
    trend = round((pr(rows[-5:]) - pr(rows[-10:-5]))*10, 2)
    return {
        "student_id": sid, "subject": subject,
        "total_classes": total, "classes_attended": att,
        "attendance_percentage": pct,
        "recent_absences": sum(1 for r in rows[-10:] if r["status"]=="absent"),
        "attendance_trend": trend, "last_updated": l["date"],
    }

def get_all_subjects_summary(sid: str) -> list:
    """Returns a summary for EVERY registered subject (including 0-record ones)."""
    student = get_student(sid)
    if not student: return []
    return [get_subject_summary(sid, s) for s in student.get("subjects", [])]

def get_overall_summary(sid: str) -> Optional[dict]:
    """Grand total across all subjects."""
    sid      = sid.upper()
    student  = get_student(sid)
    if not student: return None
    subjects = student.get("subjects", [])
    if not subjects: return None

    summaries = get_all_subjects_summary(sid)
    recorded  = [s for s in summaries if s["total_classes"] > 0]
    if not recorded:
        return {
            "student_id": sid, "total_classes": 0, "classes_attended": 0,
            "attendance_percentage": 0.0, "recent_absences": 0,
            "attendance_trend": 0.0, "subject_count": len(subjects),
            "last_updated": "No records yet",
        }

    tot  = sum(s["total_classes"]    for s in recorded)
    att  = sum(s["classes_attended"] for s in recorded)
    rows = [r for r in _load_rows() if r["student_id"]==sid]
    return {
        "student_id": sid,
        "total_classes": tot, "classes_attended": att,
        "attendance_percentage": round(att/tot*100, 2) if tot else 0.0,
        "recent_absences": sum(1 for r in rows[-10:] if r["status"]=="absent"),
        "attendance_trend": 0.0,
        "subject_count": len(subjects),
        "last_updated": rows[-1]["date"] if rows else "No records yet",
    }

def get_attendance_history(sid: str, subject: str = None) -> list:
    rows = [r for r in _load_rows() if r["student_id"]==sid.upper()]
    if subject: rows = [r for r in rows if r["subject"]==subject.strip().title()]
    out = []
    for r in rows:
        t = int(r["total_classes"]); a = int(r["classes_attended"])
        out.append({
            "date": r["date"], "status": r["status"], "subject": r["subject"],
            "total_classes": t, "classes_attended": a,
            "attendance_percentage": round(a/t*100,2) if t else 0,
        })
    return out
