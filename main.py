#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aryaboom Bot - Clan Warfare Telegram Game
مالک: @amele55 | ایدی: 8588773170
نسخه Webhook برای Render
"""

import os
import logging
import asyncio
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
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            "لیست قبایل موجود را انتخاب کن:\n"
            "(هر قبیله فقط می‌تواند یک کاربر داشته باشد)",
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
        
        try:
            clan_index = int(query.data.split("_")[1])
            context.user_data['selected_clan'] = clan_index
            
            clan_name = self.config.CLANS[clan_index]["name"]
            clan_emoji = self.config.CLANS[clan_index]["emoji"]
            
            await query.edit_message_text(
                f"{clan_emoji} قبیله انتخاب شده: <b>{clan_name}</b>\n\n"
                "📝 لطفاً <b>ایدی عددی</b> کاربر را وارد کن:\n\n"
                "<i>برای گرفتن ایدی عددی:</i>\n"
                "1. به @userinfobot برو\n"
                "2. دستور /start را بزن\n"
                "3. ایدی عددی را کپی کن\n\n"
                "یا دستور /cancel را برای لغو بزن",
                parse_mode='HTML'
            )
            return "ENTER_USER_ID"
        except Exception as e:
            logger.error(f"Error in clan selection: {e}")
            await query.edit_message_text("❌ خطا در انتخاب قبیله.")
            return ConversationHandler.END
    
    async def handle_user_id_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت ایدی کاربر از مالک"""
        user_id_input = update.message.text
        
        if user_id_input == "/cancel":
            await update.message.reply_text("❌ عملیات لغو شد.")
            return ConversationHandler.END
        
        if not user_id_input.isdigit():
            await update.message.reply_text(
                "❌ ایدی باید عددی باشد!\n"
                "لطفاً دوباره وارد کن یا /cancel بزن:",
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

📚 <b>برای شروع بازی:</b>
1. دستور /start را بزن
2. آموزش مقدماتی را بخوان
3. قلمرو خودت را توسعه بده

⚠️ <b>توجه مهم:</b>
برای ادامه بازی و دریافت اخبار باید در کانال‌های زیر عضو شوی:
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
                f"📊 <b>آمار جدید:</b>\n"
                f"👥 کاربران کل: {stats['active_users']}\n"
                f"🏛 قبایل پر: {stats['occupied_clans']}/12\n"
                f"🤖 قبایل AI: {stats['ai_clans']}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"❌ <b>خطا در ثبت کاربر:</b>\n{result['message']}",
                parse_mode='HTML'
            )
        
        return ConversationHandler.END
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                [InlineKeyboardButton("📢 عضویت در کانال اخبار", url=self.config.NEWS_CHANNEL)],
                [InlineKeyboardButton("📖 عضویت در کانال راهنما", url=self.config.GUIDE_CHANNEL)],
                [InlineKeyboardButton("👥 عضویت در کانال جامعه", url=self.config.COMMUNITY_CHANNEL)],
                [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_main")]
            ])
            
            await query.edit_message_text(
                "📢 <b>کانال‌های رسمی آریابوم</b>\n\n"
                "برای دریافت آخرین اخبار، راهنما و ارتباط با جامعه بازی:\n\n"
                "1️⃣ <b>کانال اخبار:</b> اطلاعیه‌ها، رویدادها، مسابقات\n"
                "2️⃣ <b>کانال راهنما:</b> آموزش کامل بازی، استراتژی‌ها\n"
                "3️⃣ <b>کانال جامعه:</b> گفتگو با بازیکنان دیگر\n\n"
                "⚠️ عضویت در این کانال‌ها برای ادامه بازی ضروری است.",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        elif data == "guide":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 راهنمای کامل بازی", url=self.config.GUIDE_CHANNEL)],
                [InlineKeyboardButton("🎮 شروع آموزش", callback_data="tutorial")],
                [InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_main")]
            ])
            
            await query.edit_message_text(
                "📖 <b>راهنمای بازی آریابوم</b>\n\n"
                "برای یادگیری کامل بازی و استراتژی‌های مختلف:\n\n"
                "• آموزش مقدماتی\n"
                "• راهنمای هر قبیله\n"
                "• تاکتیک‌های جنگی\n"
                "• مدیریت اقتصاد\n"
                "• سیستم اتحاد\n\n"
                "به کانال راهنما مراجعه کن یا آموزش را شروع کن.",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        elif data == "battle":
            keyboard = self.keyboards.battle_menu_keyboard()
            await query.edit_message_text(
                "⚔️ <b>منوی جنگ</b>\n\n"
                "انتخاب کن:\n\n"
                "🎯 <b>حمله:</b> حمله به قبیله دیگر\n"
                "🛡 <b>دفاع:</b> بررسی وضعیت دفاعی\n"
                "🏹 <b>آموزش نیرو:</b> آموزش نیروهای جدید\n"
                "🗺 <b>نقشه:</b> مشاهده نقشه جهان\n"
                "⚔️ <b>نبردهای فعال:</b> جنگ‌های در جریان",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        elif data == "build":
            keyboard = self.keyboards.build_menu_keyboard()
            user_data = self.db.get_user_data(user_id)
            
            await query.edit_message_text(
                f"🏗 <b>منوی ساخت‌وساز</b>\n\n"
                f"🏛 قبیله: {user_data['clan_name']}\n"
                f"📍 قلمرو: {user_data['territories']} منطقه\n\n"
                f"ساختمان‌های قابل ساخت:\n"
                f"🏯 <b>قلعه:</b> افزایش دفاع\n"
                f"🏹 <b>آموزشگاه:</b> آموزش نیروهای بهتر\n"
                f"💰 <b>بازار:</b> افزایش درآمد\n"
                f"🌾 <b>مزرعه:</b> تولید غذا\n"
                f"🪵 <b>جنگلداری:</b> تولید چوب\n"
                f"🪨 <b>معدن:</b> تولید سنگ",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        elif data == "economy":
            keyboard = self.keyboards.economy_menu_keyboard()
            user_data = self.db.get_user_data(user_id)
            
            await query.edit_message_text(
                f"💰 <b>منوی اقتصاد</b>\n\n"
                f"💰 طلا: <code>{user_data['gold']:,}</code>\n"
                f"🌾 غذا: <code>{user_data['food']:,}</code>\n"
                f"🪵 چوب: <code>{user_data['wood']:,}</code>\n"
                f"🪨 سنگ: <code>{user_data['stone']:,}</code>\n\n"
                f"عملیات اقتصادی:\n"
                f"🔄 <b>تجارت:</b> مبادله منابع\n"
                f"📈 <b>بازار:</b> خرید و فروش\n"
                f"🏛 <b>مالیات:</b> تنظیم مالیات\n"
                f"📊 <b>گزارش:</b> گزارش مالی",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        elif data == "alliance":
            keyboard = self.keyboards.alliance_menu_keyboard()
            user_data = self.db.get_user_data(user_id)
            alliance_name = user_data.get('alliance_name', 'بدون اتحاد')
            
            await query.edit_message_text(
                f"🤝 <b>منوی اتحاد</b>\n\n"
                f"اتحاد فعلی: <b>{alliance_name}</b>\n\n"
                f"عملیات اتحاد:\n"
                f"➕ <b>ایجاد اتحاد:</b> ایجاد اتحاد جدید\n"
                f"👥 <b>پیوستن:</b> پیوستن به اتحاد موجود\n"
                f"📜 <b>لیست اتحادها:</b> مشاهده اتحادهای فعال\n"
                f"🗣 <b>مذاکره:</b> مذاکره با دیگر قبایل\n"
                f"📊 <b>اعضای اتحاد:</b> مشاهده اعضای اتحاد",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        elif data == "stats":
            user_data = self.db.get_user_data(user_id)
            stats = self.db.get_user_stats(user_id)
            
            await query.edit_message_text(
                f"📊 <b>آمار شخصی</b>\n\n"
                f"🏛 قبیله: {user_data['clan_name']}\n"
                f"👑 لقب: {self.clan_manager.get_clan_title(user_data['clan_name'])}\n"
                f"🎮 کد دعوت: <code>{user_data.get('invite_code', '---')}</code>\n\n"
                f"⚔️ <b>آمار جنگی:</b>\n"
                f"• پیروزی‌ها: {stats.get('wins', 0)}\n"
                f"• شکست‌ها: {stats.get('losses', 0)}\n"
                f"• کشته‌ها: {stats.get('kills', 0)}\n\n"
                f"💰 <b>آمار اقتصادی:</b>\n"
                f"• کل درآمد: {stats.get('total_income', 0):,} طلا\n"
                f"• کل هزینه: {stats.get('total_expense', 0):,} طلا\n\n"
                f"📅 <b>تاریخچه:</b>\n"
                f"• عضو از: {user_data.get('registered_at', '---')}",
                reply_markup=self.keyboards.main_menu_keyboard(),
                parse_mode='HTML'
            )
        
        elif data == "start_game":
            await self.start(update, context)
        
        elif data == "back_to_main":
            await self.start(update, context)
        
        elif data == "admin_panel":
            await self.admin_panel(update, context)
        
        elif data == "admin_add_user":
            await self.admin_add_user(update, context)
        
        elif data.startswith("battle_"):
            await self.handle_battle_action(query, data)
    
    async def handle_battle_action(self, query, data):
        """مدیریت اقدامات جنگی"""
        action = data.split("_")[1]
        
        if action == "attack":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎯 حمله به AI", callback_data="attack_ai")],
                [InlineKeyboardButton("⚔️ حمله به بازیکن", callback_data="attack_player")],
                [InlineKeyboardButton("🏠 بازگشت", callback_data="battle")]
            ])
            
            await query.edit_message_text(
                "🎯 <b>انتخاب نوع حمله</b>\n\n"
                "🔹 <b>حمله به AI:</b> قبایل کنترل شده توسط هوش مصنوعی\n"
                "• خطر کمتر\n"
                "• غنائم متوسط\n"
                "• مناسب برای تمرین\n\n"
                "🔸 <b>حمله به بازیکن:</b> قبایل دیگر بازیکنان\n"
                "• خطر بیشتر\n"
                "• غنائم زیاد\n"
                "• افتخار و رتبه",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریت مالک"""
        user_id = update.effective_user.id
        
        if str(user_id) != self.config.OWNER_ID:
            await update.message.reply_text("⛔ دسترسی محدود!")
            return
        
        keyboard = self.keyboards.admin_panel_keyboard()
        
        # دریافت آمار کلی
        stats = self.db.get_stats()
        all_users = self.db.get_all_users()
        
        stats_text = f"""
👑 <b>پنل مدیریت آریابوم</b>
مالک: {self.config.OWNER_USERNAME}

📊 <b>آمار کلی سیستم:</b>
👥 کاربران فعال: {stats['active_users']}
🏛 قبایل پر: {stats['occupied_clans']} از 12
🤖 قبایل AI: {stats['ai_clans']}
📅 آخرین ثبت‌نام: {stats['last_registration']}

👤 <b>کاربران اخیر:</b>
"""
        
        # نمایش ۵ کاربر آخر
        for i, user in enumerate(all_users[:5], 1):
            user_id, username, clan_name, level, reg_date = user
            stats_text += f"{i}. {clan_name} | @{username or 'بدون نام'} | سطح {level}\n"
        
        if len(all_users) > 5:
            stats_text += f"\n... و {len(all_users) - 5} کاربر دیگر"
        
        await update.message.reply_text(
            stats_text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لیست کاربران برای مالک"""
        user_id = update.effective_user.id
        
        if str(user_id) != self.config.OWNER_ID:
            await update.message.reply_text("⛔ دسترسی محدود!")
            return
        
        users = self.db.get_all_users()
        
        if not users:
            await update.message.reply_text("📭 هیچ کاربری ثبت نشده است.")
            return
        
        users_text = "👥 <b>لیست کاربران آریابوم</b>\n\n"
        
        for i, user in enumerate(users, 1):
            user_id, username, clan_name, level, reg_date = user
            users_text += f"{i}. <b>{clan_name}</b>\n"
            users_text += f"   👤 @{username or 'بدون نام'}\n"
            users_text += f"   🆔 <code>{user_id}</code>\n"
            users_text += f"   🎮 سطح: {level}\n"
            users_text += f"   📅 {reg_date[:10]}\n\n"
        
        await update.message.reply_text(
            users_text,
            parse_mode='HTML'
        )
    
    def setup_handlers(self):
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
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(add_user_conv)
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # هندلرهای مالک
        self.application.add_handler(CommandHandler("panel", self.admin_panel))
        self.application.add_handler(CommandHandler("list_users", self.list_users))
        self.application.add_handler(CommandHandler("stats", self.admin_panel))
        
        # هندلر خطا
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        try:
            # اطلاع به مالک
            error_msg = (
                f"❌ <b>خطا در بات آریابوم</b>\n\n"
                f"📝 <b>خطا:</b> {str(context.error)[:500]}\n\n"
                f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await context.bot.send_message(
                chat_id=self.config.OWNER_ID,
                text=error_msg,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
    
    async def set_webhook(self):
        """تنظیم Webhook برای Render"""
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        
        await self.application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        logger.info(f"✅ Webhook set to: {webhook_url}")
        return webhook_url
    
    def create_app(self):
        """ساخت اپلیکیشن"""
        self.application = Application.builder() \
            .token(self.config.BOT_TOKEN) \
            .build()
        
        # تنظیم هندلرها
        self.setup_handlers()
        
        return self.application
    
    async def run_webhook(self):
        """اجرای بات با Webhook"""
        app = self.create_app()
        
        # تنظیم Webhook
        webhook_url = await self.set_webhook()
        
        logger.info(f"🤖 Aryaboom Bot is starting with Webhook...")
        
        # شروع Webhook
        await app.initialize()
        await app.start()
        
        PORT = int(os.getenv('PORT', 10000))
        
        await app.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=webhook_url,
            allowed_updates=Update.ALL_TYPES
        )
        
        logger.info(f"✅ Bot is running on port {PORT}")
        logger.info(f"✅ Webhook URL: {webhook_url}")
        
        # نگه داشتن برنامه
        await asyncio.Event().wait()

# تابع اصلی
async def main():
    bot = AryaboomBot()
    
    # بررسی محیط اجرا
    if os.getenv('RENDER'):
        logger.info("🚀 Running in Render environment (Webhook mode)")
        await bot.run_webhook()
    else:
        logger.info("💻 Running in local environment (Polling mode)")
        app = bot.create_app()
        await app.initialize()
        await app.start()
        logger.info("🤖 Bot is running with polling...")
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
