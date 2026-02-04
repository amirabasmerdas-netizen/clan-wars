#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aryaboom Bot - Minimal Version
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = "8588773170"

async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if str(user_id) != OWNER_ID:
        keyboard = [[InlineKeyboardButton("👑 پیام به مالک", url="https://t.me/amele55")]]
        await update.message.reply_text(
            "⛔ باید توسط مالک تأیید شوید.\nمالک: @amele55",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ افزودن کاربر", callback_data="add_user")],
        [InlineKeyboardButton("📊 آمار", callback_data="stats")]
    ]
    await update.message.reply_text(
        "👑 پنل مدیریت آریابوم",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    logger.info("Bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
