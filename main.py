import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import Config

# Import internal modules
from database import Database
from game_logic import GameLogic
from keyboards import Keyboards

# تنظیمات
config = Config()
db = Database()
game_logic = GameLogic(db)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app
flask_app = Flask(__name__)
application = None
bot = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات"""
    user = update.effective_user
    user_id = user.id
    
    keyboard = Keyboards.get_main_menu(config.OWNER_ID, user_id)
    
    if update.message:
        await update.message.reply_text(
            f"👋 سلام {user.first_name}!\n"
            f"به بازی جنگ جهانی باستان خوش آمدید.\n\n"
            f"برای ادامه از دکمه‌های زیر استفاده کنید:",
            reply_markup=keyboard
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            f"👋 سلام {user.first_name}!\n"
            f"به بازی جنگ جهانی باستان خوش آمدید.\n\n"
            f"برای ادامه از دکمه‌های زیر استفاده کنید:",
            reply_markup=keyboard
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    logger.info(f"Button clicked by {user_id}: {data}")
    
    # ... (بقیه کد button_handler که داری)
    # فقط import رو درست کردم

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # ... (بقیه کد handle_text که داری)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint برای Render"""
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json_str, bot)
    
    # Process the update
    application.process_update(update)
    return 'OK'

@flask_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'ancient-war-bot'}

def create_app():
    """ایجاد برنامه"""
    global application, bot
    
    # ایجاد برنامه Telegram
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # اضافه کردن handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    bot = Bot(token=config.BOT_TOKEN)
    
    return application

def run_polling():
    """اجرای با Polling"""
    app = create_app()
    logger.info("🤖 Starting bot with polling...")
    app.run_polling()

def run_webhook():
    """اجرای با Webhook برای Render"""
    app = create_app()
    
    # تنظیم webhook
    if config.WEBHOOK_URL:
        bot.set_webhook(url=config.WEBHOOK_URL + '/webhook')
        logger.info(f"✅ Webhook set to: {config.WEBHOOK_URL}/webhook")
    
    # اجرای Flask
    flask_app.run(host='0.0.0.0', port=config.PORT)

if __name__ == '__main__':
    # بررسی محیط اجرا
    if os.getenv('RENDER'):
        logger.info("🚀 Running in Render environment (Webhook mode)")
        run_webhook()
    else:
        logger.info("💻 Running in local environment (Polling mode)")
        run_polling()
