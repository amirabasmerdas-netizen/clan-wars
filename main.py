#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aryaboom Bot - Clan Warfare Telegram Game
مالک: @amele55 | ایدی: 8588773170
نسخه ساده شده
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# Import internal modules
from config import Config
from database import Database
from keyboards import Keyboards
from clan_manager import ClanManager

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AryaboomBot:
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.keyboards = Keyboards()
        self.clan_manager = ClanManager()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user_id = update.effective_user.id
        user = update.effective_user
        
        logger.info(f"User {user_id} (@{user.username}) started the bot")
        
        # بررسی آیا کاربر تأیید شده است
        if not self.db.is_user_verified(user_id):
            keyboard = self.keyboards.unverified_user_keyboard()
            await update.message.reply_text(
                self.config.UNVERIFIED_MESSAGE,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            return
        
        # کاربر تأیید شده
        user_data = self.db.get_user_data(user_id)
        keyboard = self.keyboards.main_menu_keyboard()
        
        welcome_text = f"""
🏛 <b>آریابوم - جنگ تمدن‌ها</b>

سلام {self.clan_manager.get_clan_title(user_data['clan_name'])}! 👑
قبیله: {user_data['clan_name']}
سطح: {user_data['level']}

💰 طلا: {user_data['gold']:,}
🌾 غذا: {user_data['food']:,}
⚔️ نیروها: {user_data['troops']:,}

برای شروع از دکمه‌های زیر استفاده کن:
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    async def admin_add_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """افزودن کاربر جدید توسط مالک"""
        user_id = update.effective_user.id
        
        # بررسی مالک بودن
        if str(user_id) != self.config.OWNER_ID:
            await update.message.reply_text("⛔ فقط مالک می‌تواند کاربر اضافه کند!")
            return
        
        keyboard = self.keyboards.clan_selection_keyboard()
        await update.message.reply_text(
            "🤴 <b>افزودن کاربر جدید</b>\n\n"
            "قبیله مورد نظر را انتخاب کن:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return "SELECT_CLAN"
    
    async def handle_clan_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """انتخاب قبیله توسط مالک"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ عملیات لغو شد.")
            return ConversationHandler.END
        
        clan_index = int(query.data.split("_")[1])
        context.user_data['selected_clan'] = clan_index
        
        clan_name = self.config.CLANS[clan_index]["name"]
        await query.edit_message_text(
            f"🏛 قبیله: <b>{clan_name}</b>\n\n"
            "لطفاً ایدی عددی کاربر را وارد کن:",
            parse_mode='HTML'
        )
        return "ENTER_USER_ID"
    
    async def handle_user_id_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت ایدی کاربر از مالک"""
        user_id_input = update.message.text
        
        if not user_id_input.isdigit():
            await update.message.reply_text("❌ ایدی باید عددی باشد!")
            return "ENTER_USER_ID"
        
        new_user_id = int(user_id_input)
        clan_index = context.user_data['selected_clan']
        
        # ثبت کاربر جدید
        result = self.db.add_new_user(
            user_id=new_user_id,
            clan_index=clan_index,
            registered_by=int(self.config.OWNER_ID)
        )
        
        if result['success']:
            # ارسال پیام به کاربر جدید
            try:
                welcome_keyboard = self.keyboards.welcome_keyboard()
                welcome_message = f"""
🎉 <b>به آریابوم خوش آمدید!</b>

🏛 قبیله شما: {result['clan_name']}
🎮 کد دعوت: {result['invite_code']}

برای شروع بازی دستور /start را بزن.
                """
                
                await context.bot.send_message(
                    chat_id=new_user_id,
                    text=welcome_message,
                    reply_markup=welcome_keyboard,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error sending welcome: {e}")
            
            await update.message.reply_text(
                f"✅ کاربر ثبت شد!\n"
                f"قبیله: {result['clan_name']}\n"
                f"کد دعوت: {result['invite_code']}"
            )
        else:
            await update.message.reply_text(f"❌ {result['message']}")
        
        return ConversationHandler.END
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت کلیک روی دکمه‌های اینلاین"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "news_channel":
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 عضویت در کانال", url=self.config.NEWS_CHANNEL)
            ]])
            await query.edit_message_text(
                "کانال رسمی اخبار بازی:",
                reply_markup=keyboard
            )
        
        elif data == "admin_panel":
            await self.admin_panel(update, context)
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریت مالک"""
        user_id = update.effective_user.id
        
        if str(user_id) != self.config.OWNER_ID:
            await update.message.reply_text("⛔ دسترسی محدود!")
            return
        
        keyboard = self.keyboards.admin_panel_keyboard()
        
        stats = self.db.get_stats()
        message = f"""
👑 <b>پنل مدیریت</b>

👥 کاربران: {stats['active_users']}
🏛 قبایل پر: {stats['occupied_clans']}
🤖 قبایل AI: {stats['ai_clans']}
        """
        
        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    def setup_handlers(self, application: Application):
        """تنظیم هندلرهای بات"""
        
        # هندلر مالک برای افزودن کاربر
        add_user_conv = ConversationHandler(
            entry_points=[CommandHandler('add_user', self.admin_add_user)],
            states={
                "SELECT_CLAN": [CallbackQueryHandler(self.handle_clan_selection)],
                "ENTER_USER_ID": [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_user_id_input)]
            },
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        # هندلرهای اصلی
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(add_user_conv)
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        application.add_handler(CommandHandler("panel", self.admin_panel))
    
    def run(self):
        """اجرای بات"""
        # ساخت اپلیکیشن
        application = Application.builder() \
            .token(self.config.BOT_TOKEN) \
            .build()
        
        # تنظیم هندلرها
        self.setup_handlers(application)
        
        # شروع بات
        logger.info("🤖 Aryaboom Bot is starting...")
        application.run_polling()

# تابع اصلی
def main():
    bot = AryaboomBot()
    bot.run()

if __name__ == '__main__':
    main()
