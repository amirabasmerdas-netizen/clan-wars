#!/usr/bin/env python3
"""
فایل اصلی اجرای ربات جنگ جهانی باستان
"""

import os
import sys
import logging

# تنظیمات اولیه لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """بررسی متغیرهای محیطی ضروری"""
    required_vars = ['BOT_TOKEN', 'OWNER_ID']
    missing_vars = []
    
    for var in required_vars:
        if var not in os.environ:
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"متغیرهای محیطی ضروری یافت نشد: {', '.join(missing_vars)}")
        logger.info("لطفاً این متغیرها را تنظیم کنید:")
        logger.info("  - BOT_TOKEN: توکن ربات تلگرام")
        logger.info("  - OWNER_ID: آیدی عددی مالک ربات")
        return False
    
    return True

def main():
    """تابع اصلی اجرای برنامه"""
    try:
        # چاپ اطلاعات شروع
        print("\n" + "="*50)
        print("🤖 Ancient War Bot - ربات جنگ جهانی باستان")
        print("="*50)
        
        # بررسی محیط
        if not check_environment():
            sys.exit(1)
        
        # نمایش اطلاعات پیکربندی
        from config import BOT_TOKEN, OWNER_ID, CHANNEL_ID, DATABASE_PATH
        
        logger.info(f"👑 مالک بازی: {OWNER_ID}")
        logger.info(f"📁 مسیر دیتابیس: {DATABASE_PATH}")
        logger.info(f"📢 کانال اطلاع‌رسانی: {CHANNEL_ID}")
        
        # بررسی webhook
        from config import WEBHOOK_URL, PORT
        
        # وارد کردن app
        from app import app, application
        
        if WEBHOOK_URL:
            # حالت production با webhook
            logger.info(f"🌐 حالت Production با Webhook")
            logger.info(f"🔗 Webhook URL: {WEBHOOK_URL}")
            logger.info(f"🚀 شروع ربات روی پورت {PORT}")
            
            # راه‌اندازی webhook
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=BOT_TOKEN,
                webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
                secret_token='ancient-war-bot-secret'
            )
        else:
            # حالت development با polling
            logger.info("🛠️ حالت Development با Polling")
            logger.info("🚀 شروع ربات...")
            
            # شروع polling
            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
    except KeyboardInterrupt:
        print("\n\n🛑 ربات با Ctrl+C متوقف شد.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
