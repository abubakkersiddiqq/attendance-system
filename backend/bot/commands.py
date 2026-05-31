"""
bot/commands.py
================
All bot commands except /register and /link (those are in registration.py):
  /start, /help
  /subjects, /addsubject, /removesubject
  /attendance, /subject
  /present, /absent
  /bunk
  /predict, /report
  /advice, /plan
  /history
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.helpers import GET, POST, require_sid, risk_emoji, pct_emoji, safe_bunks_calc
from bot.helpers import DELETE, USER_MAP

# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hello *{name}*! I am the *Attendance Bot*.\n\n"
        "I help you track your college attendance, calculate safe bunks, "
        "and predict if you are at risk - per subject.\n\n"
        "*Getting Started*\n"
        "1 - Type /register to create your profile\n"
        "2 - Add your subjects during registration\n"
        "3 - Mark attendance after each class\n\n"
        "Type /help to see all commands.",
        parse_mode="Markdown",
    )


# ── /help ─────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Bot Commands*\n\n"
        "*Setup*\n"
        "/register - Create your profile (guided steps)\n"
        "/link U19MT23S0054 - Link your roll number\n"
        "/deleteaccount - Permanently delete your account\n\n"
        "*Subjects (Settings only)*\n"
        "/subjects - List all your subjects\n"
        "/addsubject Python Programming - Add a subject\n"
        "/removesubject PHP - Remove a subject\n\n"
        "*Mark Attendance*\n"
        "/present Python Programming - Mark present\n"
        "/absent Database Management - Mark absent\n\n"
        "*Check Attendance*\n"
        "/attendance - Overall attendance percentage\n"
        "/subject Python Programming - One subject only\n\n"
        "*Bunk Calculator*\n"
        "/bunk - Safe bunks overall\n"
        "/bunk PHP - Can I bunk PHP today?\n\n"
        "*AI Features*\n"
        "/predict - ML risk prediction\n"
        "/report - Full report with all subjects\n"
        "/advice - Personalised AI advice\n"
        "/plan - What should I do today?\n\n"
        "*History*\n"
        "/history - All records\n"
        "/history PHP - PHP records only\n\n"
        "💬 *You can also chat naturally!*\n"
        "_Can I bunk PHP today?_\n"
        "_Mark me present in Python Programming_\n"
        "_What is my Database attendance?_",
        parse_mode="Markdown",
    )

# ── Subject management ────────────────────────────────────────────────────────

async def cmd_subjects(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    data = GET(f"/subjects-summary/{sid}")
    if "error" in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return

    subjects = data.get("subjects", [])
    if not subjects:
        await update.message.reply_text(
            "No subjects yet.\nUse `/addsubject SubjectName` to add one.",
            parse_mode="Markdown",
        )
        return

    lines = []
    for s in subjects:
        icon  = pct_emoji(s["attendance_percentage"])
        bunks = safe_bunks_calc(s["classes_attended"], s["total_classes"])
        lines.append(
            f"{icon} *{s['subject']}* - {s['attendance_percentage']}% "
            f"({s['classes_attended']}/{s['total_classes']}) | Bunks: {bunks}"
        )

    await update.message.reply_text(
        f"📚 *Your Subjects - {sid}*\n\n" + "\n".join(lines) +
        "\n\n_Add: /addsubject SubjectName_",
        parse_mode="Markdown",
    )


async def cmd_addsubject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    subject = " ".join(ctx.args).strip().title() if ctx.args else ""
    if not subject:
        await update.message.reply_text(
            "Usage: `/addsubject SubjectName`\n"
            "Example: `/addsubject Machine Learning`\n\n"
            "Subjects can only be added here or in the Settings tab of the web dashboard.",
            parse_mode="Markdown",
        )
        return

    result = POST("/student/add-subject", {"student_id": sid, "subject": subject})
    if "error" in result:
        await update.message.reply_text(f"❌ {result['error']}")
        return

    subjects = result.get("subjects", [])
    await update.message.reply_text(
        f"✅ *{subject}* added!\n\n"
        f"📚 Your subjects ({len(subjects)}):\n" +
        "\n".join(f"  {i+1}. {s}" for i, s in enumerate(subjects)) +
        f"\n\nUse `/present {subject}` to mark attendance.",
        parse_mode="Markdown",
    )


async def cmd_removesubject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    subject = " ".join(ctx.args).strip().title() if ctx.args else ""
    if not subject:
        await update.message.reply_text(
            "Usage: `/removesubject SubjectName`\n"
            "Example: `/removesubject PE`\n\n"
            "Subjects can only be removed here or in the Settings tab.",
            parse_mode="Markdown",
        )
        return

    result = POST("/student/remove-subject", {"student_id": sid, "subject": subject})
    if "error" in result:
        await update.message.reply_text(f"❌ {result['error']}")
        return

    await update.message.reply_text(
        f"🗑️ *{subject}* removed from your subjects.",
        parse_mode="Markdown",
    )


# ── Attendance ────────────────────────────────────────────────────────────────

async def cmd_attendance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    data = GET(f"/attendance/{sid}")
    if "error" in data:
        await update.message.reply_text(
            "❌ No attendance records yet.\n"
            "Use `/present SubjectName` to start marking attendance.",
            parse_mode="Markdown",
        )
        return

    icon = pct_emoji(data["attendance_percentage"])
    await update.message.reply_text(
        f"{icon} *Overall Attendance - {sid}*\n\n"
        f"📊 {data['attendance_percentage']}%\n"
        f"✅ {data['classes_attended']} / {data['total_classes']} classes\n"
        f"📚 Tracking {data.get('subject_count', '?')} subjects\n\n"
        "Use /subjects for a subject-wise breakdown.",
        parse_mode="Markdown",
    )


async def cmd_subject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    subj = " ".join(ctx.args).title() if ctx.args else ""
    if not subj:
        await update.message.reply_text(
            "Usage: `/subject Python Programming`\nOr type /subjects to see all.",
            parse_mode="Markdown",
        )
        return

    # Check if subject is registered
    student_data = GET(f"/subjects/{sid}")
    if "error" not in student_data:
        registered = [s.lower() for s in student_data.get("subjects", [])]
        if subj.lower() not in registered:
            subject_list = "\n".join(
                f"  - {s}" for s in student_data.get("subjects", [])
            ) or "  No subjects registered yet."
            await update.message.reply_text(
                f"❌ *{subj}* is not in your registered subjects.\n\n"
                f"Your subjects:\n{subject_list}\n\n"
                f"To add it: `/addsubject {subj}`",
                parse_mode="Markdown",
            )
            return

    data  = GET(f"/attendance/{sid}/{subj}")
    icon  = pct_emoji(data["attendance_percentage"])
    bunks = safe_bunks_calc(data["classes_attended"], data["total_classes"])

    await update.message.reply_text(
        f"{icon} *{subj} Attendance*\n\n"
        f"📊 {data['attendance_percentage']}%\n"
        f"✅ Attended: {data['classes_attended']} / {data['total_classes']}\n"
        f"⏭ Safe bunks: *{bunks}*\n"
        f"📅 Recent absences: {data['recent_absences']}\n"
        f"🕐 Last updated: {data['last_updated']}",
        parse_mode="Markdown",
    )


# ── Mark attendance ───────────────────────────────────────────────────────────

async def _mark(update: Update, ctx: ContextTypes.DEFAULT_TYPE, status: str):
    sid = await require_sid(update)
    if not sid:
        return

    subj = " ".join(ctx.args).strip().title() if ctx.args else ""
    if not subj:
        data  = GET(f"/subjects/{sid}")
        subjs = data.get("subjects", []) if "error" not in data else []
        hint  = "\n".join(f"  - /{status} {s}" for s in subjs[:5]) if subjs else ""
        await update.message.reply_text(
            f"Which subject?\n\n"
            f"Usage: `/{status} SubjectName`\n"
            f"Example: `/{status} Python Programming`\n\n"
            f"{'Your subjects:\n' + hint if hint else 'Use /subjects to see your list.'}",
            parse_mode="Markdown",
        )
        return

    result = POST("/attendance", {"student_id": sid, "status": status, "subject": subj})
    if "error" in result:
        await update.message.reply_text(f"❌ {result['error']}")
        return

    rec     = result.get("record", {})
    summary = result.get("subject_summary", {})
    emoji   = "✅" if status == "present" else "📝"
    actual  = rec.get("subject", subj)
    pct     = summary.get("attendance_percentage", 0)
    icon    = pct_emoji(pct)

    await update.message.reply_text(
        f"{emoji} Marked *{status}* in *{actual}*\n\n"
        f"{icon} {actual} attendance: *{pct}%* "
        f"({summary.get('classes_attended', 0)}/{summary.get('total_classes', 0)})",
        parse_mode="Markdown",
    )


async def cmd_present(update, ctx): await _mark(update, ctx, "present")
async def cmd_absent(update, ctx):  await _mark(update, ctx, "absent")


# ── Bunk calculator ───────────────────────────────────────────────────────────

async def cmd_bunk(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    subj = " ".join(ctx.args).title() if ctx.args else None
    data = GET(f"/bunk/{sid}/{subj}") if subj else GET(f"/bunk/{sid}")
    if "error" in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return

    bunks = data["safe_bunks"]
    emoji = "✅" if bunks > 0 else "🚨"
    label = f"*{subj}*" if subj else "overall"

    await update.message.reply_text(
        f"{emoji} *Bunk Check - {label}*\n\n"
        f"{data['message']}\n\n"
        f"📊 Current: {data['current_attendance']}%\n"
        f"🎯 Required: {data['required_percentage']}%",
        parse_mode="Markdown",
    )


# ── AI / Predict ──────────────────────────────────────────────────────────────

async def cmd_predict(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    data = GET(f"/predict/{sid}")
    if "error" in data:
        await update.message.reply_text(
            f"❌ {data['error']}\nMark some attendance first."
        )
        return

    await update.message.reply_text(
        "🤖 *ML Risk Prediction*\n\n"
        f"{risk_emoji(data['risk_level'])} Risk Level: *{data['risk_level']}*\n"
        f"📉 Probability: {data['risk_probability'] * 100:.1f}%\n\n"
        f"_{data['message']}_",
        parse_mode="Markdown",
    )


async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    await update.message.reply_text("⏳ Generating your report...")
    data = GET(f"/report/{sid}")
    if "error" in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return

    subjects   = data.get("subjects", [])
    pred       = data.get("ml_prediction", {})
    subj_lines = "\n".join(
        f"{pct_emoji(s['attendance_percentage'])} *{s['subject']}* - "
        f"{s['attendance_percentage']}% ({s['classes_attended']}/{s['total_classes']})"
        for s in subjects
    )

    await update.message.reply_text(
        f"📋 *Full Report - {data.get('student_name', sid)}*\n\n"
        f"🎓 Overall: *{data['attendance_percentage']}%* - {data['status']}\n"
        f"✅ Attended: {data['classes_attended']} / {data['total_classes']}\n"
        f"⏭ Safe bunks: *{data['safe_bunks']}*\n"
        f"📚 Recovery needed: {data['classes_needed_to_recover']} classes\n\n"
        f"*Subject Breakdown:*\n{subj_lines or '_No records yet_'}\n\n"
        f"🤖 *ML:* {risk_emoji(pred.get('risk_level', '?'))} {pred.get('risk_level', '?')}",
        parse_mode="Markdown",
    )

    advice = data.get("advice", "")
    if advice:
        await update.message.reply_text(
            f"💡 *AI Advice:*\n\n{advice}",
            parse_mode="Markdown",
        )


async def cmd_advice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    await update.message.reply_text("💭 Getting your personalised advice...")
    data = GET(f"/advice/{sid}")
    if "error" in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return

    await update.message.reply_text(
        f"💡 *Personalised Advice*\n\n{data.get('advice', 'No advice available.')}",
        parse_mode="Markdown",
    )


async def cmd_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    data = GET(f"/advice/{sid}")
    if "error" in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return

    await update.message.reply_text(
        f"📅 *Today's Plan*\n\n{data.get('today_plan', 'No plan available.')}",
        parse_mode="Markdown",
    )


# ── History ───────────────────────────────────────────────────────────────────

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return

    subj = " ".join(ctx.args).title() if ctx.args else None
    path = f"/history/{sid}/{subj}" if subj else f"/history/{sid}"
    data = GET(path)
    hist = data.get("history", [])

    if not hist:
        await update.message.reply_text(
            "No records yet. Use `/present SubjectName` to start.",
            parse_mode="Markdown",
        )
        return

    recent = list(reversed(hist[-10:]))
    lines  = []
    for r in recent:
        icon = "✅" if r["status"] == "present" else "❌"
        lines.append(
            f"{icon} {r['date']} | {r['subject']} | {r['attendance_percentage']}%"
        )

    label = f" ({subj})" if subj else ""
    await update.message.reply_text(
        f"📜 *Last {len(lines)} records{label}:*\n\n" + "\n".join(lines),
        parse_mode="Markdown",
    )
async def cmd_deleteaccount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sid = await require_sid(update)
    if not sid:
        return
    result = await DELETE(f"/students/{sid}")
    if result:
        USER_MAP.pop(update.effective_user.id, None)
        await update.message.reply_text(
            "✅ Your account and all attendance records have been permanently deleted.\n"
            "Use /register to create a new account."
        )
    else:
        await update.message.reply_text("❌ Failed to delete account. Please try again.")