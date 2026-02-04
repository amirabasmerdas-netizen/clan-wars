import os
import logging
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sqlite3
from datetime import datetime

# تنظیمات
TOKEN = os.environ.get('BOT_TOKEN', '')
OWNER_ID = 8588773170
CHANNEL_ID = os.environ.get('CHANNEL_ID', '@ancient_war_news')
ADMIN_IDS = [OWNER_ID]

# ایجاد ربات
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دیتابیس
def init_db():
    conn = sqlite3.connect('game.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول بازیکنان
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            country TEXT,
            gold INTEGER DEFAULT 100,
            iron INTEGER DEFAULT 100,
            stone INTEGER DEFAULT 100,
            food INTEGER DEFAULT 100,
            army INTEGER DEFAULT 50,
            defense INTEGER DEFAULT 50,
            join_date TIMESTAMP
        )
    ''')
    
    # جدول کشورها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            special_resource TEXT,
            controller TEXT DEFAULT 'AI',
            player_id INTEGER
        )
    ''')
    
    # کشورهای پیش‌فرض
    countries = [
        ('پارس', 'اسب'),
        ('روم', 'آهن'),
        ('مصر', 'طلا'),
        ('چین', 'غذا'),
        ('یونان', 'سنگ'),
        ('بابل', 'دانش'),
        ('آشور', 'نفت'),
        ('کارتاژ', 'کشتی'),
        ('هند', 'ادویه'),
        ('مقدونیه', 'فیل')
    ]
    
    for name, resource in countries:
        cursor.execute('INSERT OR IGNORE INTO countries (name, special_resource) VALUES (?, ?)', 
                      (name, resource))
    
    conn.commit()
    return conn

db_conn = init_db()

# منوها
def main_menu(user_id):
    keyboard = InlineKeyboardMarkup()
    
    if user_id in ADMIN_IDS:
        keyboard.row(
            InlineKeyboardButton("👑 افزودن بازیکن", callback_data="add_player"),
            InlineKeyboardButton("🌍 کشورها", callback_data="view_countries")
        )
        keyboard.row(
            InlineKeyboardButton("▶️ شروع فصل", callback_data="start_season"),
            InlineKeyboardButton("⏹️ پایان فصل", callback_data="end_season")
        )
        keyboard.row(
            InlineKeyboardButton("🔄 ریست", callback_data="reset_game")
        )
    else:
        keyboard.row(
            InlineKeyboardButton("🏛️ کشور من", callback_data="my_country"),
            InlineKeyboardButton("📊 منابع", callback_data="view_resources")
        )
        keyboard.row(
            InlineKeyboardButton("⚔️ ارتش", callback_data="army_info"),
            InlineKeyboardButton("🤝 دیپلماسی", callback_data="diplomacy")
        )
    
    return keyboard

def countries_menu():
    keyboard = InlineKeyboardMarkup()
    cursor = db_conn.cursor()
    cursor.execute('SELECT name FROM countries WHERE controller = "AI"')
    countries = cursor.fetchall()
    
    for i in range(0, len(countries), 2):
        row = []
        if i < len(countries):
            row.append(InlineKeyboardButton(f"🏛️ {countries[i][0]}", callback_data=f"select_{countries[i][0]}"))
        if i + 1 < len(countries):
            row.append(InlineKeyboardButton(f"🏛️ {countries[i+1][0]}", callback_data=f"select_{countries[i+1][0]}"))
        if row:
            keyboard.row(*row)
    
    keyboard.row(InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu"))
    return keyboard

# هندلرهای ربات
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # ثبت کاربر در دیتابیس
    cursor = db_conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO players (user_id, username, join_date) VALUES (?, ?, ?)',
                  (user_id, username, datetime.now()))
    db_conn.commit()
    
    welcome_text = f"""👋 سلام {message.from_user.first_name}!
به بازی جنگ جهانی باستان خوش آمدید.

🎮 شما: {'👑 مالک بازی' if user_id in ADMIN_IDS else '🎮 بازیکن'}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"""
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(user_id))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if call.data == "main_menu":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"منوی اصلی\nشما: {'👑 مالک' if user_id in ADMIN_IDS else '🎮 بازیکن'}",
            reply_markup=main_menu(user_id)
        )
    
    elif call.data == "add_player":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ دسترسی ممنوع!")
            return
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🏛️ انتخاب کشور برای بازیکن جدید:\n\nکشورهای آزاد:",
            reply_markup=countries_menu()
        )
    
    elif call.data.startswith("select_"):
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ دسترسی ممنوع!")
            return
        
        country_name = call.data.replace("select_", "")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"کشور '{country_name}' انتخاب شد.\n\nلطفاً آیدی عددی کاربر را ارسال کنید:"
        )
        # ذخیره کشور انتخاب شده
        bot.register_next_step_handler(call.message, lambda m: add_player_step(m, country_name))
    
    elif call.data == "view_countries":
        cursor = db_conn.cursor()
        cursor.execute('''
            SELECT c.name, c.special_resource, c.controller, 
                   COALESCE(p.username, 'بدون بازیکن') as player_name
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
        ''')
        countries = cursor.fetchall()
        
        text = "🌍 **لیست کشورهای باستانی:**\n\n"
        for name, resource, controller, player in countries:
            controller_icon = "🤖" if controller == "AI" else "👤"
            text += f"🏛️ **{name}**\n"
            text += f"   منبع ویژه: {resource}\n"
            text += f"   کنترل: {controller_icon} {player}\n"
            text += f"   {'─'*20}\n"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    elif call.data == "my_country":
        cursor = db_conn.cursor()
        cursor.execute('''
            SELECT c.name, c.special_resource, 
                   p.gold, p.iron, p.stone, p.food, p.army, p.defense
            FROM players p
            JOIN countries c ON p.country = c.name
            WHERE p.user_id = ?
        ''', (user_id,))
        
        player_data = cursor.fetchone()
        
        if player_data:
            name, resource, gold, iron, stone, food, army, defense = player_data
            text = f"""🏛️ **کشور شما: {name}**

🎁 منبع ویژه: {resource}

📊 **منابع:**
💰 طلا: {gold}
⚒️ آهن: {iron}
🪨 سنگ: {stone}
🍖 غذا: {food}

⚔️ **نظامی:**
👮 ارتش: {army}
🛡️ دفاع: {defense}"""
        else:
            text = "⚠️ شما هنوز کشوری ندارید!\nلطفاً از مالک درخواست کشور کنید."
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    elif call.data == "view_resources":
        cursor = db_conn.cursor()
        cursor.execute('SELECT gold, iron, stone, food FROM players WHERE user_id = ?', (user_id,))
        resources = cursor.fetchone()
        
        if resources:
            gold, iron, stone, food = resources
            text = f"""📊 **منابع شما:**

💰 طلا: {gold}
⚒️ آهن: {iron}
🪨 سنگ: {stone}
🍖 غذا: {food}

💡 راهنمایی: از این منابع برای ساخت ارتش و توسعه کشور استفاده کنید."""
        else:
            text = "⚠️ شما هنوز ثبت‌نام نکرده‌اید. /start را بزنید."
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    elif call.data == "start_season":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ دسترسی ممنوع!")
            return
        
        try:
            # ارسال پیام به کانال
            bot.send_message(
                CHANNEL_ID,
                "🎉 **شروع فصل جدید جنگ‌های باستان!**\n\n"
                "جهان باستان زنده شد! کشورها برای فتح جهان آماده می‌شوند...\n\n"
                "ساخته شده توسط @amele55\n"
                "ورژن 1 ربات"
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ فصل جدید با موفقیت شروع شد!\nپیام در کانال ارسال شد.",
                reply_markup=main_menu(user_id)
            )
        except Exception as e:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ خطا در شروع فصل: {str(e)}",
                reply_markup=main_menu(user_id)
            )
    
    elif call.data == "end_season":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ دسترسی ممنوع!")
            return
        
        try:
            # پیدا کردن برنده (ساده‌سازی شده)
            cursor = db_conn.cursor()
            cursor.execute('''
                SELECT p.user_id, p.username, c.name, 
                       (p.gold + p.iron + p.stone + p.food + p.army * 10 + p.defense * 5) as score
                FROM players p
                JOIN countries c ON p.country = c.name
                WHERE c.controller = 'HUMAN'
                ORDER BY score DESC
                LIMIT 1
            ''')
            winner = cursor.fetchone()
            
            if winner:
                user_id_winner, username, country, score = winner
                bot.send_message(
                    CHANNEL_ID,
                    f"""🏆 **پایان فصل جنگ‌های باستان**

👑 فاتح نهایی جهان:
🏛️ **{country}**

👤 بازیکن: {username} (ID: {user_id_winner})
📊 امتیاز: {score}

ساخته شده توسط @amele55
منتظر فصل بعد باشید
ورژن 1 ربات"""
                )
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"✅ فصل با موفقیت پایان یافت!\n🏆 برنده: {country}",
                    reply_markup=main_menu(user_id)
                )
            else:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="⚠️ هیچ بازیکن انسانی برای برنده شدن وجود ندارد!",
                    reply_markup=main_menu(user_id)
                )
        except Exception as e:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ خطا در پایان فصل: {str(e)}",
                reply_markup=main_menu(user_id)
            )
    
    elif call.data == "reset_game":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ دسترسی ممنوع!")
            return
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("✅ بله، ریست کن", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ خیر، لغو", callback_data="main_menu")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⚠️ **هشدار: ریست کامل بازی**\n\nآیا مطمئن هستید؟\nهمه داده‌ها پاک می‌شوند!",
            reply_markup=keyboard
        )
    
    elif call.data == "confirm_reset":
        if user_id not in ADMIN_IDS:
            return
        
        try:
            cursor = db_conn.cursor()
            # ریست بازیکنان
            cursor.execute('UPDATE players SET country = NULL, gold = 100, iron = 100, stone = 100, food = 100, army = 50, defense = 50')
            # ریست کشورها
            cursor.execute('UPDATE countries SET controller = "AI", player_id = NULL')
            db_conn.commit()
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ بازی با موفقیت ریست شد!\nهمه کشورها آزاد شدند.",
                reply_markup=main_menu(user_id)
            )
        except Exception as e:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ خطا در ریست بازی: {str(e)}",
                reply_markup=main_menu(user_id)
            )

def add_player_step(message, country_name):
    try:
        new_user_id = int(message.text)
        
        cursor = db_conn.cursor()
        
        # بررسی اینکه کشور آزاد است
        cursor.execute('SELECT controller FROM countries WHERE name = ?', (country_name,))
        country = cursor.fetchone()
        
        if not country or country[0] != "AI":
            bot.reply_to(message, "❌ این کشور قبلاً اشغال شده است!")
            return
        
        # اختصاص کشور به بازیکن
        cursor.execute('UPDATE countries SET controller = "HUMAN", player_id = ? WHERE name = ?',
                      (new_user_id, country_name))
        
        # به‌روزرسانی بازیکن
        cursor.execute('UPDATE players SET country = ? WHERE user_id = ?', (country_name, new_user_id))
        
        # اگر بازیکن وجود ندارد، ایجاد کن
        if cursor.rowcount == 0:
            cursor.execute('INSERT INTO players (user_id, username, country, join_date) VALUES (?, ?, ?, ?)',
                          (new_user_id, f"player_{new_user_id}", country_name, datetime.now()))
        
        db_conn.commit()
        
        # اطلاع به مالک
        bot.reply_to(message, f"✅ بازیکن با آیدی {new_user_id} به کشور '{country_name}' اضافه شد!")
        
        # اطلاع به بازیکن جدید
        try:
            bot.send_message(
                new_user_id,
                f"🎉 شما به بازی جنگ جهانی باستان اضافه شدید!\n\n"
                f"🏛️ کشور شما: {country_name}\n"
                f"برای شروع بازی /start را بزنید."
            )
        except:
            bot.reply_to(message, f"⚠️ نتوانستم به کاربر {new_user_id} پیام بدم.")
            
    except ValueError:
        bot.reply_to(message, "⚠️ لطفاً یک آیدی عددی معتبر وارد کنید!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# Webhook برای Render
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad Request', 400

@app.route('/')
def index():
    return 'Ancient War Bot is running!'

@app.route('/setwebhook')
def set_webhook():
    webhook_url = f"https://{request.host}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f'Webhook set to {webhook_url}'

# اجرای برنامه
if __name__ == '__main__':
    # در Render از محیطی استفاده می‌کنیم
    port = int(os.environ.get('PORT', 5000))
    
    if 'RENDER' in os.environ:
        # در Render، webhook را تنظیم می‌کنیم
        webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
        
        app.run(host='0.0.0.0', port=port)
    else:
        # برای توسعه محلی، polling
        logger.info("Starting bot in polling mode...")
        bot.remove_webhook()
        bot.polling(none_stop=True)
