#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aryaboom Bot - Clan Warfare Telegram Game
مالک: @amele55 | ایدی: 8588773170
نسخه سازگار با python-telegram-bot==13.15
"""

import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, Filters, CallbackContext, ConversationHandler
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
        self.application = None
    
    async def start(self, update: Update, context: CallbackContext):
        """دستور /start - صفحه اصلی بازی"""
        user_id = update.effective_user.id
        
        # بررسی آیا کاربر تأیید شده است
        if not self.db.is_user_verified(user_id):
            keyboard = self.keyboards.unverified_user_keyboard()
            await update.message.reply_text(
                self.config.UNVERIFIED_MESSAGE,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            return
        
        # کاربر تأیید شده - نمایش صفحه اصلی
        user_data = self.db.get_user_data(user_id)
        if not user_data:
            await update.message.reply_text("❌ خطا در دریافت اطلاعات کاربر.")
            return
        
        keyboard = self.keyboards.main_menu_keyboard()
        
        welcome_text = f"""
🏛 <b>آریابوم - جنگ تمدن‌ها</b>

سلام {self.clan_manager.get_clan_title(user_data['clan_name'])} {user_data['clan_name']}! 👑
{self.clan_manager.get_clan_emoji(user_data['clan_name'])} سطح: {user_data['level']} | ⚡ قدرت: {user_data['power']}

💼 <b>وضعیت فعلی:</b>
💰 طلا: <code>{user_data['gold']:,}</code>
🌾 غذا: <code>{user_data['food']:,}</code>
🪵 چوب: <code>{user_data['wood']:,}</code>
🪨 سنگ: <code>{user_data['stone']:,}</code>
⚔️ نیروها: <code>{user_data['troops']:,}</code>

📍 <b>قلمرو:</b> {user_data['territories']} منطقه
🤝 <b>اتحاد:</b> {user_data.get('alliance_name', 'بدون اتحاد')}
🎮 <b>کد دعوت:</b> <code>{user_data.get('invite_code', '---')}</code>
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    async def admin_add_user(self, update: Update, context: CallbackContext):
        """افزودن کاربر جدید توسط مالک"""
        user_id = update.effective_user.id
        
        # بررسی مالک بودن
        if str(user_id) != self.config.OWNER_ID:
            await update.message.reply_text("⛔ فقط مالک می‌تواند کاربر اضافه کند!")
            return
        
        keyboard = self.keyboards.clan_selection_keyboard()
        await update.message.reply_text(
            "🤴 <b>افزودن کاربر جدید</b>\n\n"
            "لیست قبایل موجود را انتخاب کن:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return "SELECT_CLAN"
    
    async def handle_clan_selection(self, update: Update, context: CallbackContext):
        """انتخاب قبیله توسط مالک"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ عملیات لغو شد.")
            return ConversationHandler.END
        
        try:
            clan_index = int(query.data.split("_")[1])
            context.user_data['selected_clan'] = clan_index
            
            clan_name = self.config.CLANS[clan_index]["name"]
            clan_emoji = self.config.CLANS[clan_index]["emoji"]
            
            await query.edit_message_text(
                f"{clan_emoji} قبیله انتخاب شده: <b>{clan_name}</b>\n\n"
                "📝 لطفاً <b>ایدی عددی</b> کاربر را وارد کن:\n\n"
                "<i>برای گرفتن ایدی عددی به @userinfobot مراجعه کن</i>\n\n"
                "یا دستور /cancel را برای لغو بزن",
                parse_mode='HTML'
            )
            return "ENTER_USER_ID"
        except Exception as e:
            logger.error(f"Error in clan selection: {e}")
            await query.edit_message_text("❌ خطا در انتخاب قبیله.")
            return ConversationHandler.END
    
    async def handle_user_id_input(self, update: Update, context: CallbackContext):
        """دریافت ایدی کاربر از مالک"""
        user_id_input = update.message.text
        
        if user_id_input == "/cancel":
            await update.message.reply_text("❌ عملیات لغو شد.")
            return ConversationHandler.END
        
        if not user_id_input.isdigit():
            await update.message.reply_text(
                "❌ ایدی باید عددی باشد!\nلطفاً دوباره وارد کن یا /cancel بزن:",
                parse_mode='HTML'
            )
            return "ENTER_USER_ID"
        
        new_user_id = int(user_id_input)
        clan_index = context.user_data.get('selected_clan', 0)
        
        # ثبت کاربر جدید
        result = self.db.add_new_user(
            user_id=new_user_id,
            clan_index=clan_index,
            registered_by=int(self.config.OWNER_ID)
        )
        
        if result['success']:
            try:
                # ارسال پیام خوش‌آمد به کاربر جدید
                welcome_keyboard = self.keyboards.welcome_keyboard()
                clan_title = self.clan_manager.get_clan_title(result['clan_name'])
                
                welcome_message = f"""
🎉 <b>به آریابوم خوش آمدید!</b>

🏛 <b>قبیله شما:</b> {result['clan_name']}
👑 <b>لقب شما:</b> {clan_title}
🎮 <b>کد دعوت شما:</b> <code>{result['invite_code']}</code>

برای شروع بازی دستور /start را بزن.

⚠️ <b>توجه:</b> برای ادامه بازی در کانال‌های زیر عضو شو:
                """
                
                await context.bot.send_message(
                    chat_id=new_user_id,
                    text=welcome_message,
                    reply_markup=welcome_keyboard,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error sending welcome message: {e}")
            
            # اطلاع به مالک
            stats = self.db.get_stats()
            keyboard = self.keyboards.admin_panel_keyboard()
            
            await update.message.reply_text(
                f"✅ <b>کاربر با موفقیت ثبت شد!</b>\n\n"
                f"🏛 قبیله: {result['clan_name']}\n"
                f"🆔 ایدی کاربر: <code>{new_user_id}</code>\n"
                f"🎮 کد دعوت: <code>{result['invite_code']}</code>\n\n"
                f"📊 آمار جدید:\n"
                f"👥 کاربران کل: {stats['active_users']}\n"
                f"🏛 قبایل پر: {stats['occupied_clans']}/12",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"❌ <b>خطا:</b>\n{result['message']}",
                parse_mode='HTML'
            )
        
        return ConversationHandler.END
    
    async def handle_callback(self, update: Update, context: CallbackContext):
        """مدیریت کلیک روی دکمه‌های اینلاین"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        # بررسی دسترسی کاربر
        if not self.db.is_user_verified(user_id) and data not in ["news_channel", "guide", "start_game"]:
            keyboard = self.keyboards.unverified_user_keyboard()
            await query.edit_message_text(
                self.config.UNVERIFIED_MESSAGE,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            return
        
        if data == "news_channel":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 کانال اخبار", url=self.config.NEWS_CHANNEL)],
                [InlineKeyboardButton("📖 کانال راهنما", url=self.config.GUIDE_CHANNEL)],
                [InlineKeyboardButton("👥 کانال جامعه", url=self.config.COMMUNITY_CHANNEL)],
                [InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_main")]
            ])
            
            await query.edit_message_text(
                "📢 <b>کانال‌های رسمی آریابوم</b>\n\n"
                "برای عضویت روی دکمه‌ها کلیک کن:",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        elif data == "guide":
            await query.edit_message_text(
                "📖 راهنمای کامل بازی در کانال زیر موجود است:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📖 راهنمای بازی", url=self.config.GUIDE_CHANNEL)],
                    [InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_main")]
                ]),
                parse_mode='HTML'
            )
        
        elif data == "back_to_main":
            await self.start(update, context)
        
        elif data == "start_game":
            await self.start(update, context)
    
    async def admin_panel(self, update: Update, context: CallbackContext):
        """پنل مدیریت مالک"""
        user_id = update.effective_user.id
        
        if str(user_id) != self.config.OWNER_ID:
            await update.message.reply_text("⛔ دسترسی محدود!")
            return
        
        keyboard = self.keyboards.admin_panel_keyboard()
        stats = self.db.get_stats()
        
        await update.message.reply_text(
            f"👑 <b>پنل مدیریت آریابوم</b>\n\n"
            f"📊 آمار کلی:\n"
            f"👥 کاربران فعال: {stats['active_users']}\n"
            f"🏛 قبایل پر: {stats['occupied_clans']} از 12\n"
            f"🤖 قبایل AI: {stats['ai_clans']}\n\n"
            f"دستورات مدیریت:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    async def list_users(self, update: Update, context: CallbackContext):
        """لیست کاربران برای مالک"""
        user_id = update.effective_user.id
        
        if str(user_id) != self.config.OWNER_ID:
            await update.message.reply_text("⛔ دسترسی محدود!")
            return
        
        users = self.db.get_all_users()
        
        if not users:
            await update.message.reply_text("📭 هیچ کاربری ثبت نشده است.")
            return
        
        users_text = "👥 <b>لیست کاربران</b>\n\n"
        for user in users[:10]:  # فقط 10 کاربر اول
            user_id, username, clan_name, level, power, gold, reg_date = user
            users_text += f"🏛 {clan_name}\n👤 @{username}\n🎮 سطح: {level}\n💰 طلا: {gold:,}\n\n"
        
        if len(users) > 10:
            users_text += f"\n... و {len(users) - 10} کاربر دیگر"
        
        await update.message.reply_text(users_text, parse_mode='HTML')
    
    def setup_handlers(self):
        """تنظیم هندلرهای بات"""
        
        # هندلر مالک برای افزودن کاربر
        add_user_conv = ConversationHandler(
            entry_points=[CommandHandler('add_user', self.admin_add_user)],
            states={
                "SELECT_CLAN": [CallbackQueryHandler(self.handle_clan_selection)],
                "ENTER_USER_ID": [MessageHandler(Filters.text & ~Filters.command, self.handle_user_id_input)]
            },
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        # هندلرهای اصلی
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(add_user_conv)
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # هندلرهای مالک
        self.application.add_handler(CommandHandler("panel", self.admin_panel))
        self.application.add_handler(CommandHandler("list_users", self.list_users))
        
        # هندلر خطا
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: Update, context: CallbackContext):
        """مدیریت خطاها"""
        logger.error(f"Exception: {context.error}")
        
        try:
            await context.bot.send_message(
                chat_id=self.config.OWNER_ID,
                text=f"❌ خطا در بات: {str(context.error)[:200]}"
            )
        except:
            pass
    
    def create_app(self):
        """ساخت اپلیکیشن برای نسخه 13.15"""
        self.application = Application.builder().token(self.config.BOT_TOKEN).build()
        self.setup_handlers()
        return self.application
    
    def run_polling(self):
        """اجرای بات با Polling"""
        self.application = self.create_app()
        logger.info("🤖 Bot starting with polling...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    def run_webhook(self):
        """اجرای بات با Webhook برای Render"""
        self.application = self.create_app()
        
        # تنظیم Webhook
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        
        # برای نسخه 13.15 باید از Updater استفاده کنیم
        updater = Updater(token=self.config.BOT_TOKEN, use_context=True)
        
        # اضافه کردن هندلرها به Updater
        dp = updater.dispatcher
        
        # هندلر مالک برای افزودن کاربر
        add_user_conv = ConversationHandler(
            entry_points=[CommandHandler('add_user', self.admin_add_user)],
            states={
                "SELECT_CLAN": [CallbackQueryHandler(self.handle_clan_selection)],
                "ENTER_USER_ID": [MessageHandler(Filters.text & ~Filters.command, self.handle_user_id_input)]
            },
            fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
        )
        
        # هندلرهای اصلی
        dp.add_handler(CommandHandler("start", self.start))
        dp.add_handler(add_user_conv)
        dp.add_handler(CallbackQueryHandler(self.handle_callback))
        dp.add_handler(CommandHandler("panel", self.admin_panel))
        dp.add_handler(CommandHandler("list_users", self.list_users))
        
        # هندلر خطا
        dp.add_error_handler(self.error_handler)
        
        # تنظیم Webhook
        PORT = int(os.getenv('PORT', 10000))
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=webhook_url
        )
        
        logger.info(f"🤖 Bot running on port {PORT} with webhook")
        logger.info(f"✅ Webhook URL: {webhook_url}")
        
        # نگه داشتن برنامه
        updater.idle()

# تابع اصلی ساده شده
def main():
    bot = AryaboomBot()
    
    # بررسی محیط اجرا
    if os.getenv('RENDER'):
        logger.info("🚀 Running in Render environment (Webhook mode)")
        bot.run_webhook()
    else:
        logger.info("💻 Running in local environment (Polling mode)")
        bot.run_polling()

if __name__ == '__main__':
    main()
