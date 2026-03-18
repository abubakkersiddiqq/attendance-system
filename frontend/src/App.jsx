import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ── API helpers ───────────────────────────────────────────────────────────────
async function apiFetch(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Error" }));
    throw new Error(e.detail || "Request failed");
  }
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Error" }));
    throw new Error(e.detail || "Request failed");
  }
  return r.json();
}

// ── Persist student ID across refreshes (Fix 2) ───────────────────────────────
const STORAGE_KEY = "goat_student_id";

function getSavedId() {
  try { return localStorage.getItem(STORAGE_KEY) || ""; }
  catch { return ""; }
}

function saveId(id) {
  try { localStorage.setItem(STORAGE_KEY, id); }
  catch { /* ignore */ }
}

// ── Shared components ─────────────────────────────────────────────────────────
function Card({ children, style = {} }) {
  return <div className="card" style={style}>{children}</div>;
}

function SecTitle({ icon, text }) {
  return <div className="sec-title">{icon} {text}</div>;
}

function Pill({ label, color = "#6EE7B7" }) {
  return (
    <span style={{
      background: `${color}18`, color, border: `1px solid ${color}`,
      borderRadius: 4, padding: "2px 9px", fontSize: 10, fontWeight: 700, letterSpacing: 1,
    }}>{label}</span>
  );
}

function Msg({ msg }) {
  if (!msg) return null;
  return (
    <div style={{
      fontSize: 12, padding: "7px 12px", borderRadius: 6, marginTop: 6,
      background: msg.ok ? "rgba(110,231,183,0.08)" : "rgba(248,113,113,0.08)",
      color: msg.ok ? "#6EE7B7" : "#F87171",
    }}>{msg.text}</div>
  );
}

function RingGauge({ pct, size = 130 }) {
  const r = 50, c = 2 * Math.PI * r;
  const off = c - (Math.min(pct, 100) / 100) * c;
  const color = pct >= 75 ? "#6EE7B7" : pct >= 65 ? "#FCD34D" : "#F87171";
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#1e2d3d" strokeWidth="11" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="11"
          strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"
          transform="rotate(-90 60 60)"
          style={{ transition: "stroke-dashoffset 0.8s ease" }} />
      </svg>
      <div style={{
        position: "absolute", top: 0, left: 0, width: "100%", height: "100%",
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 1,
      }}>
        <span style={{ fontFamily: "'Space Mono',monospace", fontSize: size > 110 ? 19 : 15, fontWeight: 700, color, lineHeight: 1 }}>
          {pct.toFixed(1)}%
        </span>
        <span style={{ fontSize: 8, color: "#526578", letterSpacing: 1 }}>OVERALL</span>
      </div>
    </div>
  );
}

function LineChart({ history, subject }) {
  const data = (subject ? history.filter(h => h.subject === subject) : history).slice(-20);
  if (data.length < 2) return <div className="empty-chart">Mark more attendance to see the chart.</div>;
  const W = 560, H = 130, P = 26;
  const xi = i => P + (i / (data.length - 1)) * (W - P * 2);
  const yi = v => H - P - (v / 100) * (H - P * 2);
  const line = data.map((d, i) => `${i === 0 ? "M" : "L"}${xi(i)},${yi(d.attendance_percentage)}`).join(" ");
  const area = `${line} L${xi(data.length - 1)},${H - P} L${xi(0)},${H - P} Z`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 130 }}>
      <defs>
        <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6EE7B7" stopOpacity="0.28" />
          <stop offset="100%" stopColor="#6EE7B7" stopOpacity="0" />
        </linearGradient>
      </defs>
      <line x1={P} y1={yi(75)} x2={W - P} y2={yi(75)} stroke="#F87171" strokeWidth="1.2" strokeDasharray="5,4" opacity="0.55" />
      <text x={W - P + 3} y={yi(75) + 4} fill="#F87171" fontSize="8">75%</text>
      <path d={area} fill="url(#ag)" />
      <path d={line} fill="none" stroke="#6EE7B7" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {data.map((d, i) => (
        <circle key={i} cx={xi(i)} cy={yi(d.attendance_percentage)} r="2.5"
          fill={d.attendance_percentage >= 75 ? "#6EE7B7" : "#F87171"}
          stroke="#0f1923" strokeWidth="1.5" />
      ))}
    </svg>
  );
}

// ── Subject card — always visible even at 0 ───────────────────────────────────
function SubjectCard({ s, required, onMark, marking }) {
  const pct = s.attendance_percentage;
  const color = pct >= required ? "#6EE7B7" : pct >= required - 10 ? "#FCD34D" : "#F87171";
  const bunks = s.total_classes > 0
    ? Math.max(0, Math.floor((s.classes_attended - (required / 100) * s.total_classes) / (required / 100)))
    : 0;
  return (
    <div style={{
      background: "#0f1d2a", border: `1px solid ${color}28`, borderRadius: 10,
      padding: "14px 16px", borderLeft: `3px solid ${color}`,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: "#e2f0f9" }}>{s.subject}</span>
        <span style={{ fontFamily: "'Space Mono',monospace", fontSize: 14, fontWeight: 700, color }}>
          {pct.toFixed(1)}%
        </span>
      </div>
      <div style={{ height: 5, background: "#1e3448", borderRadius: 3, overflow: "hidden", marginBottom: 8 }}>
        <div style={{ height: "100%", width: `${Math.min(pct, 100)}%`, background: color, borderRadius: 3, transition: "width 0.6s" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontSize: 11, color: "#526578" }}>
          {s.total_classes === 0
            ? "No classes recorded yet"
            : `${s.classes_attended}/${s.total_classes} attended - ${bunks} safe bunks`}
        </div>
        {/* Mark buttons always visible regardless of 0 records */}
        <div style={{ display: "flex", gap: 6 }}>
          <button disabled={marking} onClick={() => onMark("present", s.subject)}
            style={{
              padding: "4px 10px", fontSize: 11, fontWeight: 600, borderRadius: 6, cursor: "pointer",
              border: "1px solid #6EE7B7", background: "rgba(110,231,183,0.08)", color: "#6EE7B7",
              opacity: marking ? 0.4 : 1,
            }}>P</button>
          <button disabled={marking} onClick={() => onMark("absent", s.subject)}
            style={{
              padding: "4px 10px", fontSize: 11, fontWeight: 600, borderRadius: 6, cursor: "pointer",
              border: "1px solid #F87171", background: "rgba(248,113,113,0.08)", color: "#F87171",
              opacity: marking ? 0.4 : 1,
            }}>A</button>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// DASHBOARD TAB
// ═══════════════════════════════════════════════════════════════════════════
function DashboardTab({ report, onMark, marking, markMsg }) {
  if (!report) return <div className="empty-state">Enter a student ID above and click Load.</div>;
  const overall = report.overall_summary || {};
  const pct = overall.attendance_percentage || 0;
  const req = report.required_percentage || 75;
  const pred = report.ml_prediction || {};
  const riskColor = { LOW: "#6EE7B7", MEDIUM: "#FCD34D", HIGH: "#F87171", UNKNOWN: "#94A3B8" }[pred.risk_level] || "#94A3B8";
  const statusColor = { EXCELLENT: "#6EE7B7", SAFE: "#6EE7B7", WARNING: "#FCD34D", CRITICAL: "#F87171" }[report.status] || "#94A3B8";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* Student banner */}
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 42, height: 42, borderRadius: "50%", background: "rgba(110,231,183,0.1)",
            border: "2px solid #6EE7B7", display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "'Space Mono',monospace", fontSize: 17, fontWeight: 700, color: "#6EE7B7", flexShrink: 0,
          }}>
            {(report.student_name || "?")[0].toUpperCase()}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#e2f0f9" }}>{report.student_name}</div>
            <div style={{ fontSize: 11, color: "#526578", fontFamily: "'Space Mono',monospace" }}>{report.student_id}</div>
          </div>
          <Pill label={report.status || "--"} color={statusColor} />
        </div>
      </Card>

      {/* Ring + stat chips */}
      <Card>
        <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
          <RingGauge pct={pct} />
          <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {[
              { l: "Attended", v: `${overall.classes_attended || 0}/${overall.total_classes || 0}`, c: "#6EE7B7" },
              { l: "Safe Bunks", v: report.safe_bunks || 0, c: (report.safe_bunks || 0) > 0 ? "#6EE7B7" : "#F87171" },
              { l: "To Recover", v: report.classes_needed_to_recover || 0, c: "#FCD34D" },
              { l: "Required", v: `${req}%`, c: "#94A3B8" },
            ].map(x => (
              <div key={x.l} style={{ background: "#0f1d2a", border: "1px solid #1e3448", borderRadius: 8, padding: "10px 12px" }}>
                <div style={{ fontFamily: "'Space Mono',monospace", fontSize: 18, fontWeight: 700, color: x.c, lineHeight: 1 }}>{x.v}</div>
                <div style={{ fontSize: 10, color: "#526578", marginTop: 3 }}>{x.l}</div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* ML risk */}
      <Card>
        <SecTitle icon="🤖" text="ML Risk Prediction" />
        <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 12 }}>
          <Pill label={`${pred.risk_level || "?"} RISK`} color={riskColor} />
          <span style={{ fontSize: 12, color: "#526578", flex: 1 }}>{pred.message}</span>
        </div>
        <div style={{ marginTop: 10, height: 7, background: "#152232", borderRadius: 4, overflow: "hidden" }}>
          <div style={{
            height: "100%", width: `${(pred.risk_probability || 0) * 100}%`,
            background: riskColor, borderRadius: 4, transition: "width 0.8s",
          }} />
        </div>
      </Card>

      {/* AI advice */}
      {report.advice && (
        <Card style={{ borderLeft: "3px solid #6EE7B7" }}>
          <SecTitle icon="💡" text="AI Advice" />
          <p style={{ marginTop: 8, fontSize: 13, color: "#94A3B8", lineHeight: 1.65 }}>{report.advice}</p>
        </Card>
      )}

      {/* Subject cards — always render registered subjects even at 0 */}
      <Card>
        <SecTitle icon="📚" text={`Subjects (${(report.subjects || []).length})`} />
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
          {(report.subjects || []).length === 0
            ? <div className="empty-chart">No subjects yet. Go to the Settings tab to add subjects.</div>
            : (report.subjects || []).map(s => (
              <SubjectCard key={s.subject} s={s} required={req}
                onMark={onMark} marking={marking} />
            ))
          }
        </div>
        {markMsg && <Msg msg={markMsg} />}
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// HISTORY TAB
// ═══════════════════════════════════════════════════════════════════════════
function HistoryTab({ history, subjects }) {
  const [filter, setFilter] = useState("All");
  const filtered = filter === "All" ? history : history.filter(h => h.subject === filter);
  const allSubjs = ["All", ...subjects];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Card>
        <SecTitle icon="📈" text="Attendance Trend" />
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "10px 0 12px" }}>
          {allSubjs.map(s => (
            <button key={s} onClick={() => setFilter(s)} style={{
              padding: "4px 12px", borderRadius: 16, cursor: "pointer", fontSize: 11, fontWeight: 600,
              border: `1px solid ${filter === s ? "#6EE7B7" : "#1e3448"}`,
              background: filter === s ? "rgba(110,231,183,0.08)" : "transparent",
              color: filter === s ? "#6EE7B7" : "#526578",
            }}>{s}</button>
          ))}
        </div>
        <LineChart history={history} subject={filter === "All" ? null : filter} />
      </Card>

      <Card>
        <SecTitle icon="📋" text={`Records ${filter !== "All" ? `- ${filter}` : ""}`} />
        <table className="hist-table" style={{ marginTop: 10 }}>
          <thead>
            <tr><th>Date</th><th>Subject</th><th>Status</th><th>Classes</th><th>%</th></tr>
          </thead>
          <tbody>
            {[...filtered].reverse().slice(0, 15).map((r, i) => (
              <tr key={i}>
                <td>{r.date}</td>
                <td>{r.subject}</td>
                <td><span className={`status-pill ${r.status}`}>{r.status}</span></td>
                <td>{r.classes_attended}/{r.total_classes}</td>
                <td style={{ color: r.attendance_percentage >= 75 ? "#6EE7B7" : "#F87171", fontWeight: 600 }}>
                  {r.attendance_percentage}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <div className="empty-chart">No records yet.</div>}
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PREDICT TAB
// ═══════════════════════════════════════════════════════════════════════════
function PredictTab({ report }) {
  if (!report) return <div className="empty-state">Load a student first.</div>;
  const pred = report.ml_prediction || {};
  const prob = (pred.risk_probability || 0) * 100;
  const bc = { LOW: "#6EE7B7", MEDIUM: "#FCD34D", HIGH: "#F87171" }[pred.risk_level] || "#94A3B8";
  const overall = report.overall_summary || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Card>
        <SecTitle icon="🤖" text="ML Risk Analysis" />
        <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 12 }}>
          <Pill label={`${pred.risk_level || "?"} RISK`} color={bc} />
          <p style={{ fontSize: 13, color: "#94A3B8", lineHeight: 1.65 }}>{pred.message}</p>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
              <span style={{ fontSize: 11, color: "#526578" }}>Risk Probability</span>
              <span style={{ fontFamily: "'Space Mono',monospace", fontSize: 11, color: bc }}>{prob.toFixed(1)}%</span>
            </div>
            <div style={{ height: 8, background: "#152232", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${prob}%`, background: bc, borderRadius: 4, transition: "width 0.8s" }} />
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <SecTitle icon="🔍" text="Input Features" />
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          {[
            { l: "Attendance %", v: `${(overall.attendance_percentage || 0).toFixed(1)}%` },
            { l: "Recent Absences", v: overall.recent_absences || 0 },
            { l: "Total Classes", v: overall.total_classes || 0 },
            { l: "Trend", v: overall.attendance_trend || 0 },
          ].map(f => (
            <div key={f.l} style={{
              display: "flex", justifyContent: "space-between",
              padding: "8px 12px", background: "#0f1d2a", borderRadius: 6, border: "1px solid #1e3448",
            }}>
              <span style={{ fontSize: 12, color: "#526578" }}>{f.l}</span>
              <span style={{ fontFamily: "'Space Mono',monospace", fontSize: 12, color: "#c9dcea" }}>{f.v}</span>
            </div>
          ))}
        </div>
      </Card>

      {report.today_plan && (
        <Card style={{ borderLeft: "3px solid #FCD34D" }}>
          <SecTitle icon="📅" text="Today's Plan" />
          <p style={{ marginTop: 8, fontSize: 13, color: "#94A3B8", lineHeight: 1.65 }}>{report.today_plan}</p>
        </Card>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SETTINGS TAB
// ═══════════════════════════════════════════════════════════════════════════
function SettingsTab({ studentId, report, onRefresh }) {
  const [section, setSection] = useState("register");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", gap: 8 }}>
        {[["register", "Register New Student"], ["manage", "Manage Subjects"]].map(([k, l]) => (
          <button key={k} onClick={() => setSection(k)} style={{
            padding: "7px 16px", borderRadius: 20, cursor: "pointer", fontSize: 12, fontWeight: 600,
            border: `1px solid ${section === k ? "#6EE7B7" : "#1e3448"}`,
            background: section === k ? "rgba(110,231,183,0.08)" : "transparent",
            color: section === k ? "#6EE7B7" : "#526578",
          }}>{l}</button>
        ))}
      </div>
      {section === "register" && <RegisterForm onRefresh={onRefresh} />}
      {section === "manage" && <ManageSubjects studentId={studentId} report={report} onRefresh={onRefresh} />}
    </div>
  );
}

// Register form — manual roll number with live validation
function RegisterForm({ onRefresh }) {
  const [form, setForm] = useState({ sid: "", name: "", subjects: "", required: "75" });
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sidError, setSidError] = useState("");
  const [nameError, setNameError] = useState("");
  const [subjError, setSubjError] = useState("");

  const validateSid = v => {
    if (!v) return "";
    if (v.length < 4) return "Too short - minimum 4 characters";
    if (v.length > 20) return "Too long - maximum 20 characters";
    if (!/[A-Z]/.test(v)) return "Must contain at least one letter (e.g. U19MT23S0054)";
    if (!/[0-9]/.test(v)) return "Must contain at least one digit (e.g. U19MT23S0054)";
    return "";
  };

  const validateName = v => {
    if (!v.trim()) return "";
    if (v.trim().length < 2) return "At least 2 characters required";
    if (!/^[A-Za-z ]+$/.test(v.trim())) return "Letters and spaces only - no numbers or symbols";
    return "";
  };

  const validateSubjects = v => {
    if (!v.trim()) return "";
    const list = v.split(",").map(s => s.trim()).filter(Boolean);
    if (list.length === 0) return "Add at least one subject";
    if (list.length > 15) return `Maximum 15 subjects (you have ${list.length})`;
    const lower = list.map(s => s.toLowerCase());
    if (lower.some((s, i) => lower.indexOf(s) !== i)) return "Duplicate subject detected";
    for (const s of list) {
      if (s.length < 2) return `"${s}" is too short`;
      if (!/^[A-Za-z0-9 ]+$/.test(s)) return `"${s}" contains invalid characters`;
    }
    return "";
  };

  const handleSidChange = v => {
    const clean = v.toUpperCase().replace(/[^A-Z0-9]/g, "");
    setForm(f => ({ ...f, sid: clean }));
    setSidError(validateSid(clean));
  };

  const submit = async () => {
    const se = validateSid(form.sid);
    const ne = validateName(form.name);
    const sje = validateSubjects(form.subjects);
    if (!form.sid) { setMsg({ ok: false, text: "Roll number is required" }); return; }
    if (se) { setMsg({ ok: false, text: se }); return; }
    if (!form.name.trim()) { setMsg({ ok: false, text: "Full name is required" }); return; }
    if (ne) { setMsg({ ok: false, text: ne }); return; }
    if (!form.subjects.trim()) { setMsg({ ok: false, text: "Add at least one subject" }); return; }
    if (sje) { setMsg({ ok: false, text: sje }); return; }

    const subjects = form.subjects.split(",").map(s => s.trim()).filter(Boolean);
    setLoading(true); setMsg(null);
    try {
      await apiPost("/student/create", {
        student_id: form.sid, name: form.name.trim(),
        subjects, required_percentage: parseFloat(form.required) || 75,
      });
      setMsg({ ok: true, text: `Student ${form.sid} registered successfully!` });
      setForm({ sid: "", name: "", subjects: "", required: "75" });
      setSidError(""); setNameError(""); setSubjError("");
      onRefresh(form.sid);
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    } finally {
      setLoading(false);
    }
  };

  const fields = [
    {
      key: "sid", label: "COLLEGE ROLL NUMBER *",
      placeholder: "e.g. U19MT23S0054",
      hint: form.sid.length === 0
        ? "Format: U19MT23S0054 - University + College Code + Batch Year + Serial"
        : !sidError && form.sid.length >= 4
          ? "Valid format"
          : sidError,
      hintColor: !sidError && form.sid.length >= 4 ? "#6EE7B7" : "#F87171",
      mono: true,
      onChange: e => handleSidChange(e.target.value),
      borderColor: sidError ? "#F87171" : "#1e3448",
    },
    {
      key: "name", label: "FULL NAME * (letters and spaces only)",
      placeholder: "e.g. Arjun Sharma",
      hint: nameError,
      hintColor: "#F87171",
      mono: false,
      onChange: e => { setForm(f => ({ ...f, name: e.target.value })); setNameError(validateName(e.target.value)); },
      borderColor: nameError ? "#F87171" : "#1e3448",
    },
    {
      key: "subjects", label: "SUBJECTS * (comma separated)",
      placeholder: "Python Programming, PHP, Database Management",
      hint: subjError,
      hintColor: "#F87171",
      mono: false,
      onChange: e => { setForm(f => ({ ...f, subjects: e.target.value })); setSubjError(validateSubjects(e.target.value)); },
      borderColor: subjError ? "#F87171" : "#1e3448",
    },
    {
      key: "required", label: "REQUIRED ATTENDANCE %",
      placeholder: "75",
      hint: "", hintColor: "#526578", mono: true,
      onChange: e => setForm(f => ({ ...f, required: e.target.value })),
      borderColor: "#1e3448",
    },
  ];

  return (
    <Card>
      <SecTitle icon="👤" text="Register New Student" />
      <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
        {fields.map(f => (
          <div key={f.key}>
            <label style={{ fontSize: 10, color: "#526578", display: "block", marginBottom: 4, letterSpacing: 0.5 }}>
              {f.label}
            </label>
            <input value={form[f.key]} onChange={f.onChange} placeholder={f.placeholder}
              style={{
                width: "100%", background: "#152232", border: `1px solid ${f.borderColor}`,
                borderRadius: 8, padding: "9px 12px", color: "#c9dcea", fontSize: 13, outline: "none",
                fontFamily: f.mono ? "'Space Mono',monospace" : "inherit",
              }} />
            {f.hint && (
              <div style={{ fontSize: 10, color: f.hintColor, marginTop: 3 }}>{f.hint}</div>
            )}
          </div>
        ))}
        <button onClick={submit} disabled={loading || !!sidError || !!nameError || !!subjError}
          style={{
            background: "#6EE7B7", color: "#0b1520", border: "none", borderRadius: 8,
            padding: "10px", fontWeight: 700, fontSize: 14, cursor: "pointer", marginTop: 4,
            opacity: (loading || !!sidError || !!nameError || !!subjError) ? 0.5 : 1,
          }}>
          {loading ? "Creating..." : "Create Student"}
        </button>
        <Msg msg={msg} />
      </div>
    </Card>
  );
}

// Manage subjects — add/remove with instant refresh (Fix 1)
function ManageSubjects({ studentId, report, onRefresh }) {
  const [newSubj, setNewSubj] = useState("");
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const subjects = report?.registered_subjects || [];

  const addSubject = async () => {
    if (!newSubj.trim()) { setMsg({ ok: false, text: "Enter a subject name" }); return; }
    if (!studentId) { setMsg({ ok: false, text: "Load a student first" }); return; }
    setLoading(true); setMsg(null);
    try {
      await apiPost("/student/add-subject", { student_id: studentId, subject: newSubj.trim() });
      setMsg({ ok: true, text: `"${newSubj.trim()}" added!` });
      setNewSubj("");
      // Fix 1: immediately refresh so new subject card appears without page reload
      onRefresh(studentId);
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    } finally {
      setLoading(false);
    }
  };

  const removeSubject = async subj => {
    if (!window.confirm(`Remove "${subj}" from your subjects?`)) return;
    setLoading(true); setMsg(null);
    try {
      await apiPost("/student/remove-subject", { student_id: studentId, subject: subj });
      setMsg({ ok: true, text: `"${subj}" removed.` });
      // Fix 1: immediately refresh
      onRefresh(studentId);
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <SecTitle icon="📚" text="Manage Subjects" />
      <p style={{ fontSize: 11, color: "#526578", marginTop: 4, marginBottom: 14, lineHeight: 1.5 }}>
        Subjects can only be added or removed here. They appear on the Dashboard immediately after saving.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 14 }}>
        {subjects.length === 0
          ? <div style={{ fontSize: 12, color: "#526578", padding: "10px 0" }}>No subjects yet. Add one below.</div>
          : subjects.map(s => (
            <div key={s} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "9px 12px", background: "#0f1d2a", border: "1px solid #1e3448", borderRadius: 8,
            }}>
              <span style={{ fontSize: 13, color: "#c9dcea" }}>{s}</span>
              <button onClick={() => removeSubject(s)} disabled={loading}
                style={{
                  padding: "3px 10px", fontSize: 10, fontWeight: 600, borderRadius: 5, cursor: "pointer",
                  border: "1px solid #F87171", background: "rgba(248,113,113,0.08)", color: "#F87171",
                  opacity: loading ? 0.4 : 1,
                }}>Remove</button>
            </div>
          ))
        }
      </div>

      <div style={{ borderTop: "1px solid #1e3448", paddingTop: 14 }}>
        <label style={{ fontSize: 10, color: "#526578", display: "block", marginBottom: 6, letterSpacing: 0.5 }}>
          ADD NEW SUBJECT
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <input value={newSubj} onChange={e => setNewSubj(e.target.value)}
            onKeyDown={e => e.key === "Enter" && addSubject()}
            placeholder="e.g. Machine Learning"
            style={{
              flex: 1, background: "#152232", border: "1px solid #1e3448",
              borderRadius: 8, padding: "9px 12px", color: "#c9dcea", fontSize: 13, outline: "none",
            }} />
          <button onClick={addSubject} disabled={loading || !newSubj.trim()}
            style={{
              background: "#6EE7B7", color: "#0b1520", border: "none", borderRadius: 8,
              padding: "9px 16px", fontWeight: 700, fontSize: 13, cursor: "pointer",
              opacity: (loading || !newSubj.trim()) ? 0.5 : 1,
            }}>Add</button>
        </div>
        <Msg msg={msg} />
      </div>
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════════════════
const TABS = ["Dashboard", "History", "Predict", "Settings"];

export default function App() {
  // Fix 2: read saved ID from localStorage on first load
  const [studentId, setStudentId] = useState(() => getSavedId() || "");
  const [inputId,   setInputId]   = useState(() => getSavedId() || "");
  const [tab,       setTab]       = useState("Dashboard");
  const [report,    setReport]    = useState(null);
  const [history,   setHistory]   = useState([]);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const [marking,   setMarking]   = useState(false);
  const [markMsg,   setMarkMsg]   = useState(null);

  const fetchAll = useCallback(async id => {
    if (!id) return;
    setLoading(true); setError(null);
    try {
      const [rep, hist] = await Promise.all([
        apiFetch(`/report/${id}`),
        apiFetch(`/history/${id}`).catch(() => ({ history: [] })),
      ]);
      setReport(rep);
      setHistory(hist.history || []);
    } catch (e) {
      setError(e.message);
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load on mount if we have a saved ID
  useEffect(() => {
    if (studentId) fetchAll(studentId);
  }, [studentId, fetchAll]);

  const handleSearch = e => {
    e.preventDefault();
    const id = inputId.trim().toUpperCase();
    if (!id) return;
    saveId(id);           // Fix 2: persist to localStorage
    setStudentId(id);
  };

  // Fix 1: mark attendance then immediately re-fetch — no page reload needed
  const handleMark = async (status, subject) => {
    setMarking(true); setMarkMsg(null);
    try {
      await apiPost("/attendance", { student_id: studentId, status, subject });
      setMarkMsg({ ok: true, text: `Marked ${status} in ${subject}` });
      await fetchAll(studentId);   // instant refresh
    } catch (e) {
      setMarkMsg({ ok: false, text: e.message });
    } finally {
      setMarking(false);
    }
  };

  // Fix 1: after adding/removing subject, re-fetch immediately
  const handleRefresh = id => {
    const target = id || studentId;
    saveId(target);       // Fix 2: also persist when registering new student
    setStudentId(target);
    setInputId(target);
    setTab("Dashboard");
    fetchAll(target);
  };

  return (
    <div className="root">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-goat">GOAT</span>
          <span className="brand-sub">Attendance AI</span>
        </div>
        <nav className="nav">
          {TABS.map(t => (
            <div key={t} className={`nav-item ${tab === t ? "active" : ""}`}
              onClick={() => setTab(t)}>{t}</div>
          ))}
        </nav>
        {report && (
          <div style={{ marginTop: "auto", padding: "12px 8px", borderTop: "1px solid #1e3448" }}>
            <div style={{ fontSize: 9, color: "#526578", letterSpacing: 1, marginBottom: 3 }}>LOADED STUDENT</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#c9dcea" }}>{report.student_name}</div>
            <div style={{ fontSize: 10, fontFamily: "'Space Mono',monospace", color: "#526578", marginTop: 1 }}>{studentId}</div>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="main">
        <header className="topbar">
          <div>
            <div className="page-title">{tab}</div>
            <div className="page-sub">
              {{ Dashboard: "Real-time tracking & subject breakdown", History: "Records & trend chart", Predict: "AI risk analysis", Settings: "Register students & manage subjects" }[tab]}
            </div>
          </div>
          <form onSubmit={handleSearch} className="search-form">
            <input value={inputId}
              onChange={e => setInputId(e.target.value.toUpperCase())}
              placeholder="Roll number..."
              className="search-input"
              style={{ fontFamily: "'Space Mono',monospace", letterSpacing: 1 }} />
            <button type="submit" className="search-btn">Load</button>
          </form>
        </header>

        {loading && <div className="loading-bar"><div className="loading-inner" /></div>}
        {error   && <div className="error-banner">Student not found. Check the roll number or use the Settings tab to register.</div>}

        {tab === "Dashboard" && (
          <DashboardTab report={report} onMark={handleMark} marking={marking} markMsg={markMsg} />
        )}
        {tab === "History" && (
          history.length > 0
            ? <HistoryTab history={history} subjects={report?.registered_subjects || []} />
            : <div className="empty-state">No history yet. Mark attendance from the Dashboard.</div>
        )}
        {tab === "Predict"  && <PredictTab report={report} />}
        {tab === "Settings" && (
          <SettingsTab studentId={studentId} report={report} onRefresh={handleRefresh} />
        )}
      </main>
    </div>
  );
}
