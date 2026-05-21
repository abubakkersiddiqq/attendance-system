"""
main.py — FastAPI Backend v2 (subject-aware)
=============================================
New endpoints:
  POST /student/register          → register with name + subjects list
  GET  /subjects/{student_id}     → list student's subjects
  POST /attendance                → mark present/absent for a subject
  GET  /attendance/{id}           → overall summary
  GET  /attendance/{id}/{subject} → per-subject summary
  GET  /bunk/{id}                 → overall safe bunks
  GET  /bunk/{id}/{subject}       → safe bunks for one subject
  GET  /predict/{id}              → ML risk prediction
  GET  /report/{id}               → full report
  GET  /history/{id}              → full history (all subjects)
  GET  /history/{id}/{subject}    → history for one subject
  GET  /students                  → list all students
  GET  /health                    → health check
  POST /student/create            → create with validated roll number
  POST /student/add-subject       → add subject to existing student
  POST /student/remove-subject    → remove subject
  POST /student/update-threshold  → change required %
  GET  /advice/{student_id}       → LLM smart advice
  GET  /plan/{student_id}         → LLM today's plan
  GET  /llm/status                → check if LLM is configured
"""


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import storage, attendance_engine, prediction_model, llm_service

app = FastAPI(title="GOAT Attendance API v3", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ================= Request models =======================

class StudentCreate(BaseModel):
    student_id:          str
    name:                str
    subjects:            List[str] = []
    required_percentage: float = 75.0

class SubjectAction(BaseModel):
    student_id: str
    subject:    str

class ThresholdUpdate(BaseModel):
    student_id:          str
    required_percentage: float

class AttendanceIn(BaseModel):
    student_id: str
    status:     str          # "present" | "absent"
    subject:    str


# ================= Health ======================

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0",
            "llm": llm_service.llm_status()}


# ================= Student management ===================

@app.post("/student/create")
def create_student(req: StudentCreate):
    """
    Create a brand-new student.
    Validates: roll number format, uniqueness (blocked if exists), name, subjects.
    """
    student, err = storage.create_student(
        req.student_id, req.name,
        req.subjects, req.required_percentage)
    if err:
        raise HTTPException(400, err)
    return {"message": "Student created successfully", "student": student}


@app.get("/validate/student-id/{sid}")
def validate_student_id(sid: str):
    """
    Live-validate a roll number as the user types.
    Returns {valid: bool, message: str}
    Used by the registration form for real-time feedback.
    """
    ok, result = storage.validate_student_id(sid)
    if not ok:
        return {"valid": False, "message": result}
    if storage.student_exists(result):
        return {"valid": False,
                "message": f"Roll number '{result}' is already registered. "
                           f"Use the Load button to view that student."}
    return {"valid": True, "message": "Roll number is available"}


@app.get("/validate/name/{name}")
def validate_name(name: str):
    """Live-validate a name field. Returns {valid: bool, message: str}"""
    ok, result = storage.validate_name(name)
    return {"valid": ok, "message": "" if ok else result}


@app.post("/student/add-subject")
def add_subject(req: SubjectAction):
    """Add a new subject to an existing student (Settings tab only)."""
    ok, msg = storage.add_subject_to_student(req.student_id, req.subject)
    if not ok:
        raise HTTPException(400, msg)
    student = storage.get_student(req.student_id)
    return {"message": msg, "subjects": student["subjects"]}


@app.post("/student/remove-subject")
def remove_subject(req: SubjectAction):
    """Remove a subject from a student's list."""
    ok, msg = storage.remove_subject_from_student(req.student_id, req.subject)
    if not ok:
        raise HTTPException(400, msg)
    student = storage.get_student(req.student_id)
    return {"message": msg, "subjects": student["subjects"]}


@app.post("/student/update-threshold")
def update_threshold(req: ThresholdUpdate):
    """Change the required attendance percentage."""
    ok, msg = storage.update_required_percentage(
        req.student_id, req.required_percentage)
    if not ok:
        raise HTTPException(400, msg)
    return {"message": msg}


@app.get("/student/{student_id}")
def get_student(student_id: str):
    s = storage.get_student(student_id)
    if not s:
        raise HTTPException(404, f"Student '{student_id}' not found")
    return s


@app.get("/subjects/{student_id}")
def get_subjects(student_id: str):
    s = storage.get_student(student_id)
    if not s:
        raise HTTPException(404, f"Student '{student_id}' not found")
    return {"student_id": student_id, "name": s["name"],
            "subjects": s.get("subjects", [])}


# ================= Attendance =========================

@app.post("/attendance")
def mark_attendance(req: AttendanceIn):
    """
    Mark present or absent for a specific subject.
    Subject is validated and matched against the student's registered list.
    If the subject doesn't exist yet, it is auto-added.
    """
    rec, err = storage.add_attendance_record(
        req.student_id, req.status, req.subject)
    if err:
        raise HTTPException(400, err)
    # Return updated subject summary alongside the record
    summary = storage.get_subject_summary(req.student_id, rec["subject"])
    return {"message": "Attendance recorded", "record": rec,
            "subject_summary": summary}


@app.get("/attendance/{student_id}")
def overall_attendance(student_id: str):
    s = storage.get_overall_summary(student_id)
    if not s:
        raise HTTPException(404, f"No data for '{student_id}'")
    return s


@app.get("/attendance/{student_id}/{subject}")
def subject_attendance(student_id: str, subject: str):
    """Always returns data — 0s if no records yet (Bug 1 fix)."""
    return storage.get_subject_summary(student_id, subject)


@app.get("/subjects-summary/{student_id}")
def all_subjects_summary(student_id: str):
    """All subjects including ones with 0 records (Bug 2 fix)."""
    student = storage.get_student(student_id)
    if not student:
        raise HTTPException(404, f"Student '{student_id}' not found")
    return {"student_id": student_id,
            "subjects": storage.get_all_subjects_summary(student_id)}


# ================= Bunk ===================

@app.get("/bunk/{student_id}")
def bunk_overall(student_id: str):
    s       = storage.get_overall_summary(student_id)
    if not s: raise HTTPException(404, f"No data for '{student_id}'")
    student = storage.get_student(student_id)
    req_pct = (student or {}).get("required_percentage", 75.0)
    bunks   = attendance_engine.calculate_safe_bunks(
        s["classes_attended"], s["total_classes"], req_pct/100)
    return {"student_id": student_id, "safe_bunks": bunks,
            "current_attendance": s["attendance_percentage"],
            "required_percentage": req_pct,
            "message": (f"You can skip {bunks} more class(es) overall."
                        if bunks > 0 else
                        "You cannot skip any more classes right now!")}


@app.get("/bunk/{student_id}/{subject}")
def bunk_subject(student_id: str, subject: str):
    subj    = subject.strip().title()
    summary = storage.get_subject_summary(student_id, subj)
    student = storage.get_student(student_id)
    req_pct = (student or {}).get("required_percentage", 75.0)
    bunks   = attendance_engine.calculate_safe_bunks(
        summary["classes_attended"], summary["total_classes"], req_pct/100)
    return {"student_id": student_id, "subject": subj, "safe_bunks": bunks,
            "current_attendance": summary["attendance_percentage"],
            "required_percentage": req_pct,
            "message": (
                f"Yes! You can skip {bunks} more {subj} class(es)."
                if bunks > 0 else
                f"No! Attend {subj} — your attendance is too low."
            )}


# ================= Predict ============================

@app.get("/predict/{student_id}")
def predict(student_id: str):
    s = storage.get_overall_summary(student_id)
    if not s: raise HTTPException(404, f"No data for '{student_id}'")
    try:
        result = prediction_model.predict_risk(
            s["attendance_percentage"], s["recent_absences"],
            s["total_classes"],         s["attendance_trend"])
    except FileNotFoundError as e:
        raise HTTPException(500, str(e))
    return {"student_id": student_id, **result,
            "attendance_percentage": s["attendance_percentage"]}


# ================= Full report =========================

@app.get("/report/{student_id}")
def full_report(student_id: str):
    overall = storage.get_overall_summary(student_id)
    student = storage.get_student(student_id)
    if not student:
        raise HTTPException(404, f"Student '{student_id}' not found")

    req_pct  = student.get("required_percentage", 75.0)
    calc     = attendance_engine.get_full_attendance_report(
        (overall or {}).get("classes_attended", 0),
        (overall or {}).get("total_classes", 0),
        req_pct)

    try:
        pred = prediction_model.predict_risk(
            (overall or {}).get("attendance_percentage", 0),
            (overall or {}).get("recent_absences", 0),
            (overall or {}).get("total_classes", 0),
            (overall or {}).get("attendance_trend", 0))
    except FileNotFoundError:
        pred = {"risk_level": "UNKNOWN", "message": "Model not loaded",
                "risk_probability": 0, "at_risk": False}

    subjects = storage.get_all_subjects_summary(student_id)

    report = {
        "student_id":           student_id,
        "student_name":         student.get("name", "Unknown"),
        "registered_subjects":  student.get("subjects", []),
        "required_percentage":  req_pct,
        **calc,
        "ml_prediction":        pred,
        "overall_summary":      overall,
        "subjects":             subjects,
    }

    # Attach LLM advice (graceful fallback if not configured)
    report["advice"]     = llm_service.get_smart_advice(student["name"], report)
    report["today_plan"] = llm_service.get_today_plan(student["name"], report)

    return report


# ============= LLM endpoints ========================

@app.get("/advice/{student_id}")
def get_advice(student_id: str):
    """Get LLM-powered personalised advice."""
    rep = full_report(student_id)  # reuse report endpoint
    return {"student_id": student_id,
            "advice":     rep.get("advice", ""),
            "today_plan": rep.get("today_plan", "")}


@app.get("/llm/status")
def llm_status():
    return llm_service.llm_status()


# ====================== History =====================

@app.get("/history/{student_id}")
def history_all(student_id: str):
    h = storage.get_attendance_history(student_id)
    return {"student_id": student_id, "history": h}


@app.get("/history/{student_id}/{subject}")
def history_subject(student_id: str, subject: str):
    h = storage.get_attendance_history(student_id, subject)
    return {"student_id": student_id, "subject": subject, "history": h}


@app.get("/students")
def list_students():
    return {"students": storage.get_all_students()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
