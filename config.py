import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # اطلاعات مالک
    OWNER_ID = int(os.getenv('OWNER_ID', '8588773170'))
    OWNER_USERNAME = os.getenv('OWNER_USERNAME', '@amele55')
    
    # توکن بات تلگرام
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # کانال‌های رسمی
    NEWS_CHANNEL = os.getenv('NEWS_CHANNEL', 'https://t.me/Aryaboom_News')
    GUIDE_CHANNEL = os.getenv('GUIDE_CHANNEL', 'https://t.me/Aryaboom_Guide')
    COMMUNITY_CHANNEL = os.getenv('COMMUNITY_CHANNEL', 'https://t.me/Aryaboom_Community')
    CHANNEL_ID = os.getenv('CHANNEL_ID', '')
    
    # تنظیمات بازی
    MAX_PLAYERS = 12
    INITIAL_RESOURCES = {
        'gold': 1000,
        'iron': 500,
        'stone': 300,
        'food': 800,
        'army': 100,
        'defense': 50
    }
    
    # Webhook
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    PORT = int(os.getenv('PORT', 10000))

# متغیرهای global
BOT_TOKEN = Config.BOT_TOKEN
OWNER_ID = Config.OWNER_ID
CHANNEL_ID = Config.CHANNEL_ID
