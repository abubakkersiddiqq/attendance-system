import os
import re
from datetime import datetime
from typing import Optional
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from dotenv import load_dotenv

# ── Connection ────────────────────────────────────────────────────────────────
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
DB_NAME     = os.getenv("DB_NAME", "attendance")

_client = None
_db     = None


def get_db():
    """Return the database instance. Creates connection once and reuses it."""
    global _client, _db
    if _db is None:
        if not MONGODB_URI:
            raise ValueError(
                "MONGODB_URI is not set. "
            )
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _db     = _client[DB_NAME]
        _db["attendance"].create_index(
            [("student_id", ASCENDING), ("subject", ASCENDING)]
        )
        _db["students"].create_index("student_id", unique=True)
    return _db


def students_col() -> Collection:
    return get_db()["students"]


def attendance_col() -> Collection:
    return get_db()["attendance"]


# ── Validation ────────────────────────────────────────────────────────────────

def validate_student_id(sid: str) -> tuple:
    sid = sid.strip().upper()
    if not re.match(r"^[A-Z0-9]{4,20}$", sid):
        return False, "Roll number must be 4-20 characters, letters and digits only (e.g. U19MT23S0054)"
    if not re.search(r"[A-Z]", sid):
        return False, "Roll number must contain at least one letter (e.g. U19MT23S0054)"
    if not re.search(r"[0-9]", sid):
        return False, "Roll number must contain at least one digit (e.g. U19MT23S0054)"
    return True, sid


def parse_college_roll_number(sid: str) -> dict:
    sid = sid.strip().upper()
    m   = re.match(r"^([A-Z])([0-9]{2}[A-Z]{2,4})([0-9]{2})([A-Z][0-9]{3,6})$", sid)
    if not m:
        return {}
    return {
        "university_prefix": m.group(1),
        "college_code":      m.group(2),
        "batch_year":        str(2000 + int(m.group(3))),
        "serial":            m.group(4),
        "formatted": (
            f"University: {m.group(1)} | "
            f"College: {m.group(2)} | "
            f"Batch: {2000 + int(m.group(3))} | "
            f"Serial: {m.group(4)}"
        ),
    }


def validate_name(name: str) -> tuple:
    name = name.strip()
    if not name:
        return False, "Name cannot be empty."
    if len(name) < 2:
        return False, "Name must be at least 2 characters."
    if len(name) > 60:
        return False, "Name must be 60 characters or less."
    if not re.match(r"^[A-Za-z ]+$", name):
        return False, "Name must contain letters and spaces only - no numbers or symbols."
    return True, name


def validate_subjects(raw_subjects: list) -> tuple:
    cleaned = [s.strip().title() for s in raw_subjects if s.strip()]
    if not cleaned:
        return False, [], "Please add at least one subject."
    if len(cleaned) > 15:
        return False, [], f"Maximum 15 subjects allowed. You entered {len(cleaned)}."
    for s in cleaned:
        if len(s) < 2:
            return False, [], f"Subject '{s}' is too short (minimum 2 characters)."
        if len(s) > 50:
            return False, [], f"Subject '{s}' is too long (maximum 50 characters)."
        if not re.match(r"^[A-Za-z0-9 ]+$", s):
            return False, [], f"Subject '{s}' contains invalid characters."
    seen = []
    for s in cleaned:
        if s.lower() in [x.lower() for x in seen]:
            return False, [], f"Duplicate subject: '{s}' appears more than once."
        seen.append(s)
    return True, cleaned, ""


# ── Students ──────────────────────────────────────────────────────────────────

def get_student(sid: str) -> Optional[dict]:
    doc = students_col().find_one({"student_id": sid.upper()})
    if doc:
        doc.pop("_id", None)
    return doc


def student_exists(sid: str) -> bool:
    return students_col().count_documents({"student_id": sid.upper()}) > 0


def create_student(sid: str, name: str,
                   subjects: list,
                   required_percentage: float = 75.0) -> tuple:
    ok, result = validate_student_id(sid)
    if not ok:
        return {}, result
    sid = result

    if student_exists(sid):
        existing = get_student(sid)
        return {}, (
            f"Roll number '{sid}' is already registered "
            f"under the name '{existing['name']}'. "
            f"Each student can only register once. "
            f"If this is you, use /link {sid} to connect."
        )

    ok, name = validate_name(name)
    if not ok:
        return {}, name

    ok, cleaned_subjects, err = validate_subjects(subjects)
    if not ok:
        return {}, err

    doc = {
        "student_id":          sid,
        "name":                name,
        "required_percentage": required_percentage,
        "subjects":            cleaned_subjects,
        "created_at":          datetime.now().isoformat(),
    }
    students_col().insert_one({**doc})
    return doc, ""


def add_subject_to_student(sid: str, subject: str) -> tuple:
    sid     = sid.upper()
    subject = subject.strip().title()
    student = get_student(sid)
    if not student:
        return False, f"Student '{sid}' not found."
    if not subject or len(subject) < 2:
        return False, "Subject name must be at least 2 characters."
    if len(subject) > 50:
        return False, "Subject name must be 50 characters or less."
    if not re.match(r"^[A-Za-z0-9 ]+$", subject):
        return False, "Subject name must contain letters, digits and spaces only."
    existing = student.get("subjects", [])
    if len(existing) >= 15:
        return False, "Maximum 15 subjects allowed. Remove one before adding a new one."
    if subject.lower() in [s.lower() for s in existing]:
        return False, f"'{subject}' is already in your subjects list."
    students_col().update_one(
        {"student_id": sid},
        {"$push": {"subjects": subject}}
    )
    return True, f"'{subject}' added successfully."


def remove_subject_from_student(sid: str, subject: str) -> tuple:
    sid     = sid.upper()
    subject = subject.strip().title()
    student = get_student(sid)
    if not student:
        return False, f"Student '{sid}' not found."
    existing = student.get("subjects", [])
    match    = next((s for s in existing if s.lower() == subject.lower()), None)
    if not match:
        return False, f"'{subject}' not found in your subjects list."
    students_col().update_one(
        {"student_id": sid},
        {"$pull": {"subjects": match}}
    )
    return True, f"'{match}' removed successfully."


def update_required_percentage(sid: str, pct: float) -> tuple:
    sid = sid.upper()
    if not student_exists(sid):
        return False, "Student not found."
    if not (50.0 <= pct <= 100.0):
        return False, "Required percentage must be between 50 and 100."
    students_col().update_one(
        {"student_id": sid},
        {"$set": {"required_percentage": pct}}
    )
    return True, f"Required attendance updated to {pct}%."


def get_all_students() -> list:
    return list(students_col().find({}, {"_id": 0}))


# ── Attendance ────────────────────────────────────────────────────────────────

def _find_subject(query: str, registered: list) -> Optional[str]:
    q = query.strip().lower()
    for s in registered:
        if s.lower() == q:
            return s
    for s in registered:
        if q in s.lower() or s.lower() in q:
            return s
    return None


def add_attendance_record(sid: str, status: str, subject: str) -> tuple:
    sid     = sid.upper()
    subject = subject.strip().title()
    student = get_student(sid)
    if not student:
        return {}, f"Student '{sid}' not found."
    if status not in ("present", "absent"):
        return {}, "Status must be 'present' or 'absent'."

    registered = student.get("subjects", [])
    match      = _find_subject(subject, registered)
    if not match:
        add_subject_to_student(sid, subject)
        match = subject

    last = attendance_col().find_one(
        {"student_id": sid, "subject": match},
        sort=[("_id", -1)]
    )
    prev_total    = last["total_classes"]    if last else 0
    prev_attended = last["classes_attended"] if last else 0

    new_total    = prev_total + 1
    new_attended = prev_attended + (1 if status == "present" else 0)

    doc = {
        "student_id":       sid,
        "date":             datetime.now().strftime("%Y-%m-%d"),
        "status":           status,
        "subject":          match,
        "total_classes":    new_total,
        "classes_attended": new_attended,
    }
    attendance_col().insert_one({**doc})
    return doc, ""


# ── Summaries ─────────────────────────────────────────────────────────────────

def get_subject_summary(sid: str, subject: str) -> dict:
    """Always returns a summary - zeros if no records yet."""
    sid     = sid.upper()
    subject = subject.strip().title()

    last = attendance_col().find_one(
        {"student_id": sid, "subject": subject},
        sort=[("_id", -1)]
    )

    if not last:
        return {
            "student_id":            sid,
            "subject":               subject,
            "total_classes":         0,
            "classes_attended":      0,
            "attendance_percentage": 0.0,
            "recent_absences":       0,
            "attendance_trend":      0.0,
            "last_updated":          "No records yet",
        }

    total    = last["total_classes"]
    attended = last["classes_attended"]
    pct      = round(attended / total * 100, 2) if total else 0.0

    recent_records = list(attendance_col().find(
        {"student_id": sid, "subject": subject},
        {"_id": 0, "status": 1},
        sort=[("_id", -1)],
        limit=10
    ))
    recent_records.reverse()

    pr              = lambda sl: sum(1 for r in sl if r["status"] == "present") / len(sl) if sl else 0
    trend           = round((pr(recent_records[-5:]) - pr(recent_records[:5])) * 10, 2)
    recent_absences = sum(1 for r in recent_records if r["status"] == "absent")

    return {
        "student_id":            sid,
        "subject":               subject,
        "total_classes":         total,
        "classes_attended":      attended,
        "attendance_percentage": pct,
        "recent_absences":       recent_absences,
        "attendance_trend":      trend,
        "last_updated":          last["date"],
    }


def get_all_subjects_summary(sid: str) -> list:
    student = get_student(sid)
    if not student:
        return []
    return [get_subject_summary(sid, s) for s in student.get("subjects", [])]


def get_overall_summary(sid: str) -> Optional[dict]:
    sid     = sid.upper()
    student = get_student(sid)
    if not student:
        return None

    subjects  = student.get("subjects", [])
    if not subjects:
        return None

    summaries = get_all_subjects_summary(sid)
    recorded  = [s for s in summaries if s["total_classes"] > 0]

    if not recorded:
        return {
            "student_id":            sid,
            "total_classes":         0,
            "classes_attended":      0,
            "attendance_percentage": 0.0,
            "recent_absences":       0,
            "attendance_trend":      0.0,
            "subject_count":         len(subjects),
            "last_updated":          "No records yet",
        }

    total    = sum(s["total_classes"]    for s in recorded)
    attended = sum(s["classes_attended"] for s in recorded)

    recent = list(attendance_col().find(
        {"student_id": sid},
        {"_id": 0, "status": 1},
        sort=[("_id", -1)],
        limit=10
    ))
    recent_absences = sum(1 for r in recent if r["status"] == "absent")

    last_record = attendance_col().find_one(
        {"student_id": sid},
        sort=[("_id", -1)]
    )

    return {
        "student_id":            sid,
        "total_classes":         total,
        "classes_attended":      attended,
        "attendance_percentage": round(attended / total * 100, 2) if total else 0.0,
        "recent_absences":       recent_absences,
        "attendance_trend":      0.0,
        "subject_count":         len(subjects),
        "last_updated":          last_record["date"] if last_record else "No records yet",
    }


def get_attendance_history(sid: str, subject: str = None) -> list:
    sid   = sid.upper()
    query = {"student_id": sid}
    if subject:
        query["subject"] = subject.strip().title()

    records = list(attendance_col().find(
        query,
        {"_id": 0},
        sort=[("_id", ASCENDING)]
    ))

    result = []
    for r in records:
        t = r["total_classes"]
        a = r["classes_attended"]
        result.append({
            "date":                  r["date"],
            "status":                r["status"],
            "subject":               r["subject"],
            "total_classes":         t,
            "classes_attended":      a,
            "attendance_percentage": round(a / t * 100, 2) if t else 0,
        })
    return result

def delete_student(sid: str):
    db = get_db()
    db.students.delete_one({"student_id": sid})
    db.attendance.delete_many({"student_id": sid})
    return True