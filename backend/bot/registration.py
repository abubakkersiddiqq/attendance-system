"""
bot/registration.py
====================
Handles the guided /register conversation (4 steps):
  Step 1 - Roll number (validated)
  Step 2 - Full name (letters only)
  Step 3 - Subjects (comma separated)
  Step 4 - Confirm and save

Also handles /link command.
"""

import re
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, ContextTypes

from bot.helpers import GET, POST, USER_MAP

# Conversation states
REG_ID, REG_NAME, REG_SUBJECTS, REG_CONFIRM = range(4)


# ── /register entry point ─────────────────────────────────────────────────────

async def reg_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *New Student Registration*\n\n"
        "*Step 1 of 3* - Enter your *college roll number*\n\n"
        "Your college format:\n"
        "`U19MT23S0054`\n"
        "- `U` - University prefix\n"
        "- `19MT` - College code\n"
        "- `23` - Batch year\n"
        "- `S0054` - Serial number\n\n"
        "Letters and digits only, 4-20 characters.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return REG_ID


# ── Step 1 — Roll number ──────────────────────────────────────────────────────

async def reg_get_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from storage import validate_student_id, parse_college_roll_number

    sid = update.message.text.strip().upper()
    ok, result = validate_student_id(sid)

    if not ok:
        await update.message.reply_text(
            "❌ *Invalid roll number*\n\n"
            f"{result}\n\n"
            "Expected format: `U19MT23S0054`\n\n"
            "Please enter your roll number again:",
            parse_mode="Markdown",
        )
        return REG_ID

    sid = result  # normalised uppercase

    # Block if already registered
    existing = GET(f"/student/{sid}")
    if "error" not in existing:
        await update.message.reply_text(
            "❌ *Roll number already registered*\n\n"
            f"`{sid}` is already registered under the name *{existing['name']}*.\n\n"
            "Each student can only register once.\n"
            f"If this is you, type:\n`/link {sid}`",
            parse_mode="Markdown",
        )
        return REG_ID

    ctx.user_data["reg_sid"] = sid

    # Show parsed breakdown if it matches college format
    parsed = parse_college_roll_number(sid)
    breakdown = ""
    if parsed:
        breakdown = (
            "\n\n🔍 *Parsed:*\n"
            f"- University prefix: `{parsed['university_prefix']}`\n"
            f"- College code: `{parsed['college_code']}`\n"
            f"- Batch year: `{parsed['batch_year']}`\n"
            f"- Serial: `{parsed['serial']}`"
        )

    await update.message.reply_text(
        f"✅ Roll number accepted: *{sid}*{breakdown}\n\n"
        "*Step 2 of 3* - Enter your *full name*:",
        parse_mode="Markdown",
    )
    return REG_NAME


# ── Step 2 — Name ─────────────────────────────────────────────────────────────

async def reg_get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()

    if len(name) < 2:
        await update.message.reply_text(
            "Name is too short. Please enter your full name (at least 2 characters):"
        )
        return REG_NAME

    if not re.match(r"^[A-Za-z ]+$", name):
        await update.message.reply_text(
            "❌ *Invalid name*\n\n"
            "Name must contain *letters and spaces only* - no numbers or symbols.\n"
            "Example: `Arjun Sharma`\n\n"
            "Please enter your name again:",
            parse_mode="Markdown",
        )
        return REG_NAME

    if len(name) > 60:
        await update.message.reply_text(
            "Name is too long (maximum 60 characters). Please try again:"
        )
        return REG_NAME

    ctx.user_data["reg_name"] = name
    await update.message.reply_text(
        f"✅ Name: *{name}*\n\n"
        "*Step 3 of 3* - Enter your *subjects*, separated by commas.\n\n"
        "Example:\n"
        "`Python Programming, PHP, Database Management, Data Structures`\n\n"
        "Rules:\n"
        "- Minimum 1 subject, maximum 15\n"
        "- No duplicate subjects\n"
        "- Letters, digits and spaces only\n\n"
        "You can add more subjects later using /addsubject",
        parse_mode="Markdown",
    )
    return REG_SUBJECTS


# ── Step 3 — Subjects ─────────────────────────────────────────────────────────

async def reg_get_subjects(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from storage import validate_subjects

    raw_list = [s.strip() for s in update.message.text.strip().split(",")]
    ok, subjects, err = validate_subjects(raw_list)

    if not ok:
        await update.message.reply_text(
            f"❌ {err}\n\n"
            "Please re-enter your subjects separated by commas.\n"
            "Example:\n"
            "`Python Programming, PHP, Database Management`",
            parse_mode="Markdown",
        )
        return REG_SUBJECTS

    ctx.user_data["reg_subjects"] = subjects
    subj_preview = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(subjects))

    await update.message.reply_text(
        "📋 *Confirm your profile:*\n\n"
        f"🆔 Roll Number: `{ctx.user_data['reg_sid']}`\n"
        f"👤 Name: {ctx.user_data['reg_name']}\n"
        f"📚 Subjects ({len(subjects)}):\n{subj_preview}\n"
        "🎯 Required attendance: 75%\n\n"
        "Type *yes* to confirm or *no* to cancel.",
        parse_mode="Markdown",
    )
    return REG_CONFIRM


# ── Step 4 — Confirm ──────────────────────────────────────────────────────────

async def reg_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text not in ("yes", "y", "confirm", "ok"):
        await update.message.reply_text(
            "Registration cancelled. Type /register to start again."
        )
        return ConversationHandler.END

    sid      = ctx.user_data["reg_sid"]
    name     = ctx.user_data["reg_name"]
    subjects = ctx.user_data["reg_subjects"]

    result = POST("/student/create", {
        "student_id":          sid,
        "name":                name,
        "subjects":            subjects,
        "required_percentage": 75.0,
    })

    if "error" in result:
        await update.message.reply_text(
            f"❌ Registration failed: {result['error']}"
        )
        return ConversationHandler.END

    USER_MAP[update.effective_user.id] = sid
    subj_list = ", ".join(subjects[:3])
    if len(subjects) > 3:
        subj_list += f" +{len(subjects) - 3} more"

    await update.message.reply_text(
        "🎉 *Profile created successfully!*\n\n"
        f"🆔 Roll Number: `{sid}`\n"
        f"👤 Name: {name}\n"
        f"📚 Subjects: {subj_list}\n\n"
        "*Next steps:*\n"
        f"- /present {subjects[0]} - mark attendance\n"
        "- /addsubject Machine Learning - add more subjects\n"
        "- /attendance - check your percentage\n"
        "- /help - all commands",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def reg_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Registration cancelled. Type /register to start again.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ── /link ─────────────────────────────────────────────────────────────────────

async def cmd_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text(
            "Usage: `/link YOUR_ROLL_NUMBER`\nExample: `/link U19MT23S0054`",
            parse_mode="Markdown",
        )
        return

    sid  = ctx.args[0].strip().upper()
    data = GET(f"/student/{sid}")
    if "error" in data:
        await update.message.reply_text(
            f"❌ Student `{sid}` not found.\n\n"
            "If you are new, use /register to create a profile first.",
            parse_mode="Markdown",
        )
        return

    USER_MAP[uid] = sid
    await update.message.reply_text(
        f"🔗 Linked! You are now *{data['name']}* (`{sid}`)\n\n"
        "Type /help to see what you can do.",
        parse_mode="Markdown",
    )
