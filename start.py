import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات - در Render Variables تنظیم می‌شود
BOT_TOKEN = "YOUR_BOT_TOKEN"  # اینجا را تغییر دهید
OWNER_ID = 8588773170

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🏛️ مشاهده کشورها", callback_data="view_countries")],
        [InlineKeyboardButton("📊 منابع من", callback_data="my_resources")],
        [InlineKeyboardButton("⚔️ ارتش من", callback_data="my_army")],
        [InlineKeyboardButton("👑 افزودن بازیکن (مالک)", callback_data="add_player")] if user.id == OWNER_ID else []
    ]
    
    # حذف ردیف خالی
    keyboard = [row for row in keyboard if row]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 سلام {user.first_name}!\n"
        f"به بازی جنگ جهانی باستان خوش آمدید.\n\n"
        f"شما: {'👑 مالک' if user.id == OWNER_ID else '🎮 بازیکن'}",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "view_countries":
        countries = [
            "🏛️ پارس - منبع ویژه: اسب",
            "🏛️ روم - منبع ویژه: آهن",
            "🏛️ مصر - منبع ویژه: طلا",
            "🏛️ چین - منبع ویژه: غذا",
            "🏛️ یونان - منبع ویژه: سنگ"
        ]
        
        await query.edit_message_text(
            "🌍 **کشورهای باستانی:**\n\n" + "\n".join(countries)
        )
    
    elif query.data == "my_resources":
        await query.edit_message_text(
            "📊 **منابع شما:**\n\n"
            "💰 طلا: 100\n"
            "⚒️ آهن: 100\n"
            "🪨 سنگ: 100\n"
            "🍖 غذا: 100"
        )
    
    elif query.data == "my_army":
        await query.edit_message_text(
            "⚔️ **ارتش شما:**\n\n"
            "👮 سرباز پیاده: 50\n"
            "🏹 کماندار: 30\n"
            "🐎 سواره نظام: 20\n"
            "🛡️ دفاع: 50"
        )
    
    elif query.data == "add_player":
        if user_id != OWNER_ID:
            await query.edit_message_text("⛔ دسترسی ممنوع!")
            return
        
        await query.edit_message_text(
            "👑 **افزودن بازیکن جدید:**\n\n"
            "لطفاً آیدی عددی کاربر را ارسال کنید:"
        )
        context.user_data['awaiting_user_id'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id == OWNER_ID and context.user_data.get('awaiting_user_id'):
        try:
            new_user_id = int(text)
            context.user_data['awaiting_user_id'] = False
            
            await update.message.reply_text(
                f"✅ بازیکن با آیدی {new_user_id} اضافه شد!\n"
                f"اکنون کشورها را مدیریت کنید."
            )
        except ValueError:
            await update.message.reply_text("⚠️ لطفاً یک آیدی عددی معتبر وارد کنید!")
    else:
        await update.message.reply_text(
            "لطفاً از دکمه‌های منو استفاده کنید.\n"
            "برای شروع مجدد: /start"
        )

def main():
    """تابع اصلی"""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("⚠️ لطفاً BOT_TOKEN را در فایل start.py تنظیم کنید!")
        return
    
    # ایجاد برنامه
    application = Application.builder().token(BOT_TOKEN).build()
    
    # اضافه کردن handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # اجرای ربات
    print("🤖 ربات در حال راه‌اندازی...")
    print(f"🔑 مالک: {OWNER_ID}")
    print("🔄 در حالت Polling...")
    
    application.run_polling()

if __name__ == '__main__':
    main()
