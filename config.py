import os

# تنظیمات مالک ربات
OWNER_ID = 8588773170
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '@your_channel_username')

# تنظیمات دیتابیس
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'game.db')

# لیست کشورهای باستانی
ANCIENT_COUNTRIES = [
    {'id': 1, 'name': 'پارس', 'special_resource': 'اسب', 'color': '#FFD700'},
    {'id': 2, 'name': 'روم', 'special_resource': 'آهن', 'color': '#C0C0C0'},
    {'id': 3, 'name': 'مصر', 'special_resource': 'طلا', 'color': '#FFFF00'},
    {'id': 4, 'name': 'چین', 'special_resource': 'غذا', 'color': '#FF0000'},
    {'id': 5, 'name': 'یونان', 'special_resource': 'سنگ', 'color': '#0000FF'},
    {'id': 6, 'name': 'بابل', 'special_resource': 'دانش', 'color': '#800080'},
    {'id': 7, 'name': 'آشور', 'special_resource': 'نفت', 'color': '#A52A2A'},
    {'id': 8, 'name': 'کارتاژ', 'special_resource': 'کشتی', 'color': '#008000'},
    {'id': 9, 'name': 'هند', 'special_resource': 'ادویه', 'color': '#FFA500'},
    {'id': 10, 'name': 'مقدونیه', 'special_resource': 'فیل', 'color': '#808080'},
]

# تنظیمات منابع اولیه
BASE_RESOURCES = {
    'gold': 100,
    'iron': 100,
    'stone': 100,
    'food': 100
}

# تنظیمات فصل
SEASON_DURATION = 7  # روز

# تنظیمات سرور
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
PORT = int(os.environ.get('PORT', 5000))
