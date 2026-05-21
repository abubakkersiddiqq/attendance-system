"""
bot_handler.py
==============
Entry point for the Telegram bot.
This file only does two things:
  1. Register all command handlers
  2. Start polling

All logic lives in the bot/ package:
  bot/helpers.py          - API calls, intent detection, emoji helpers
  bot/registration.py     - /register conversation + /link
  bot/commands.py         - all other slash commands
  bot/natural_language.py - free-text message handler

To run the bot:
  python bot_handler.py
"""

from dotenv import load_dotenv
load_dotenv()

import os
import llm_service

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from bot.registration import (
    reg_start, reg_get_id, reg_get_name,
    reg_get_subjects, reg_confirm, reg_cancel,
    cmd_link,
    REG_ID, REG_NAME, REG_SUBJECTS, REG_CONFIRM,
)
from bot.commands import (
    cmd_start, cmd_help,
    cmd_subjects, cmd_addsubject, cmd_removesubject,
    cmd_attendance, cmd_subject,
    cmd_present, cmd_absent,
    cmd_bunk,
    cmd_predict, cmd_report, cmd_advice, cmd_plan,
    cmd_history,
)
from bot.natural_language import handle_message

TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TOKEN_HERE")
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")


async def main():
    print("🤖 Attendance Bot starting...")
    print(f"   Backend : {BACKEND}")
    print(f"   LLM     : {'ENABLED' if llm_service.LLM_ENABLED else 'DISABLED (set OPENROUTER_API_KEY to enable)'}")

    app = Application.builder().token(TOKEN).build()

    # ── Registration conversation (4 steps) ───────────────────────────────────
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("register", reg_start)],
        states={
            REG_ID:       [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_id)],
            REG_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_name)],
            REG_SUBJECTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_get_subjects)],
            REG_CONFIRM:  [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_confirm)],
        },
        fallbacks=[CommandHandler("cancel", reg_cancel)],
    )
    app.add_handler(reg_conv)

    # ── Slash commands ────────────────────────────────────────────────────────
    for cmd, fn in [
        ("start",         cmd_start),
        ("help",          cmd_help),
        ("link",          cmd_link),
        ("subjects",      cmd_subjects),
        ("addsubject",    cmd_addsubject),
        ("removesubject", cmd_removesubject),
        ("attendance",    cmd_attendance),
        ("subject",       cmd_subject),
        ("present",       cmd_present),
        ("absent",        cmd_absent),
        ("bunk",          cmd_bunk),
        ("predict",       cmd_predict),
        ("report",        cmd_report),
        ("advice",        cmd_advice),
        ("plan",          cmd_plan),
        ("history",       cmd_history),
    ]:
        app.add_handler(CommandHandler(cmd, fn))

    # ── Natural language fallback ─────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running. Press Ctrl+C to stop.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()


async def start_bot():
    await main()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())