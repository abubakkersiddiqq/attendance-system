"""
bot/natural_language.py
========================
Handles all free-text (non-command) messages.
Detects intent and routes to the right command function.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.helpers import USER_MAP, detect_intent
from bot.commands import (
    cmd_attendance, cmd_subject, cmd_bunk, cmd_predict,
    cmd_report, cmd_subjects, cmd_addsubject, cmd_removesubject,
    cmd_history, cmd_advice, cmd_plan, cmd_present, cmd_absent,
    cmd_help,
)
from bot.registration import reg_start


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Entry point for all plain-text messages.
    1. Detect intent using LLM or keyword matching
    2. Extract subject if mentioned
    3. Route to the correct command handler
    """
    uid    = update.effective_user.id
    text   = update.message.text.strip()
    sid    = USER_MAP.get(uid)
    parsed = detect_intent(text, sid)
    intent = parsed.get("intent", "unknown")
    subj   = parsed.get("subject")

    # Registration does not need a linked profile
    if intent == "register":
        await reg_start(update, ctx)
        return

    # All other intents require a linked profile
    if not sid:
        await update.message.reply_text(
            "🔗 Please register first!\nUse /register to get started.",
            parse_mode="Markdown",
        )
        return

    # Route based on detected intent
    if intent == "attendance":
        ctx.args = subj.split() if subj else []
        if subj:
            await cmd_subject(update, ctx)
        else:
            await cmd_attendance(update, ctx)

    elif intent == "bunk":
        ctx.args = subj.split() if subj else []
        await cmd_bunk(update, ctx)

    elif intent == "predict":
        await cmd_predict(update, ctx)

    elif intent == "report":
        await cmd_report(update, ctx)

    elif intent == "subjects":
        await cmd_subjects(update, ctx)

    elif intent == "add_subject":
        ctx.args = subj.split() if subj else []
        await cmd_addsubject(update, ctx)

    elif intent == "remove_subject":
        ctx.args = subj.split() if subj else []
        await cmd_removesubject(update, ctx)

    elif intent == "history":
        ctx.args = subj.split() if subj else []
        await cmd_history(update, ctx)

    elif intent == "advice":
        await cmd_advice(update, ctx)

    elif intent == "plan":
        await cmd_plan(update, ctx)

    elif intent == "mark_present":
        if subj:
            ctx.args = subj.split()
            await cmd_present(update, ctx)
        else:
            await update.message.reply_text(
                "Which subject?\nExample: _Mark me present in Python Programming_",
                parse_mode="Markdown",
            )

    elif intent == "mark_absent":
        if subj:
            ctx.args = subj.split()
            await cmd_absent(update, ctx)
        else:
            await update.message.reply_text(
                "Which subject?\nExample: _Mark absent in Database Management_",
                parse_mode="Markdown",
            )

    elif intent == "help":
        await cmd_help(update, ctx)

    elif intent == "link":
        await update.message.reply_text(
            "Usage: `/link YOUR_ROLL_NUMBER`\nExample: `/link U19MT23S0054`",
            parse_mode="Markdown",
        )

    else:
        await update.message.reply_text(
            "🤔 Not sure what you mean. Try:\n\n"
            "- _Can I bunk PHP today?_\n"
            "- _Mark me present in Python Programming_\n"
            "- _What is my Database attendance?_\n"
            "- _Add Machine Learning to my subjects_\n\n"
            "Or type /help for all commands.",
            parse_mode="Markdown",
        )
