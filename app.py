import os
import logging
import random
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from datetime import datetime

# تنظیمات
TOKEN = os.environ.get('BOT_TOKEN', '')
OWNER_ID = 8588773170
CHANNEL_ID = os.environ.get('CHANNEL_ID', '@ancient_war_news')

# ایجاد ربات
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== توابع کمکی ==========
def init_db():
    conn = sqlite3.connect('game.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول بازیکنان
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            country TEXT,
            gold INTEGER DEFAULT 1000,
            iron INTEGER DEFAULT 500,
            stone INTEGER DEFAULT 500,
            food INTEGER DEFAULT 1000,
            wood INTEGER DEFAULT 500,
            army_infantry INTEGER DEFAULT 50,
            army_archer INTEGER DEFAULT 30,
            army_cavalry INTEGER DEFAULT 20,
            army_spearman INTEGER DEFAULT 40,
            army_thief INTEGER DEFAULT 10,
            defense_wall INTEGER DEFAULT 50,
            defense_tower INTEGER DEFAULT 20,
            defense_gate INTEGER DEFAULT 30,
            mine_gold_level INTEGER DEFAULT 1,
            mine_iron_level INTEGER DEFAULT 1,
            mine_stone_level INTEGER DEFAULT 1,
            farm_level INTEGER DEFAULT 1,
            barracks_level INTEGER DEFAULT 1,
            join_date TIMESTAMP,
            last_active TIMESTAMP,
            diplomacy_notifications INTEGER DEFAULT 1
        )
    ''')
    
    # جدول کشورها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            special_resource TEXT,
            controller TEXT DEFAULT 'AI',
            player_id INTEGER,
            capital_x INTEGER,
            capital_y INTEGER
        )
    ''')
    
    # جدول نبردها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS battles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER,
            defender_id INTEGER,
            attacker_country TEXT,
            defender_country TEXT,
            result TEXT,
            attacker_losses TEXT,
            defender_losses TEXT,
            gold_looted INTEGER,
            iron_looted INTEGER,
            food_looted INTEGER,
            battle_date TIMESTAMP
        )
    ''')
    
    # جدول دیپلماسی
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diplomacy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_player_id INTEGER,
            to_player_id INTEGER,
            from_country TEXT,
            to_country TEXT,
            relation_type TEXT,
            status TEXT DEFAULT 'pending',
            message TEXT,
            created_at TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    # جدول معادن
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            country TEXT,
            mine_type TEXT,
            level INTEGER DEFAULT 1,
            last_collected TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(user_id)
        )
    ''')
    
    # کشورهای پیش‌فرض
    countries = [
        ('پارس', 'اسب', 100, 100),
        ('روم', 'آهن', 200, 100),
        ('مصر', 'طلا', 100, 200),
        ('چین', 'غذا', 200, 200),
        ('یونان', 'سنگ', 150, 150),
        ('بابل', 'دانش', 50, 150),
        ('آشور', 'نفت', 150, 50),
        ('کارتاژ', 'کشتی', 250, 100),
        ('هند', 'ادویه', 100, 250),
        ('مقدونیه', 'فیل', 200, 50)
    ]
    
    for name, resource, x, y in countries:
        cursor.execute('INSERT OR IGNORE INTO countries (name, special_resource, capital_x, capital_y) VALUES (?, ?, ?, ?)', 
                      (name, resource, x, y))
    
    conn.commit()
    return conn

db_conn = init_db()

# ========== توابع محاسباتی ==========
def calculate_army_power(player_data):
    """محاسبه قدرت کلی ارتش"""
    power = (
        player_data['army_infantry'] * 1 +
        player_data['army_archer'] * 1.5 +
        player_data['army_cavalry'] * 2 +
        player_data['army_spearman'] * 1.2 +
        player_data['army_thief'] * 0.8
    )
    return power

def calculate_defense_power(player_data):
    """محاسبه قدرت دفاع"""
    defense = (
        player_data['defense_wall'] * 1 +
        player_data['defense_tower'] * 2 +
        player_data['defense_gate'] * 1.5
    )
    return defense

def calculate_daily_production(user_id):
    """محاسبه تولید روزانه"""
    cursor = db_conn.cursor()
    cursor.execute('''
        SELECT mine_gold_level, mine_iron_level, mine_stone_level, 
               farm_level, barracks_level, country,
               gold, iron, stone, food, wood
        FROM players WHERE user_id = ?
    ''', (user_id,))
    
    player = cursor.fetchone()
    
    if not player:
        return None
    
    mine_gold, mine_iron, mine_stone, farm, barracks, country, gold, iron, stone, food, wood = player
    
    # تولید پایه
    production = {
        'gold': mine_gold * 50,
        'iron': mine_iron * 30,
        'stone': mine_stone * 40,
        'food': farm * 100,
        'wood': 20  # تولید پایه چوب
    }
    
    # اعمال بونس کشور
    if country:
        cursor.execute('SELECT special_resource FROM countries WHERE name = ?', (country,))
        country_data = cursor.fetchone()
        if country_data:
            resource = country_data[0]
            if resource == 'طلا':
                production['gold'] = int(production['gold'] * 1.5)
            elif resource == 'آهن':
                production['iron'] = int(production['iron'] * 1.5)
            elif resource == 'غذا':
                production['food'] = int(production['food'] * 1.5)
            elif resource == 'سنگ':
                production['stone'] = int(production['stone'] * 1.5)
    
    return production

def simulate_battle(attacker_data, defender_data):
    """شبیه‌سازی نبرد با جزئیات کامل"""
    # استخراج داده‌ها
    att_infantry, att_archer, att_cavalry, att_spearman, att_thief = attacker_data[:5]
    def_infantry, def_archer, def_cavalry, def_spearman, def_thief = defender_data[:5]
    def_wall, def_tower, def_gate = defender_data[5:8]
    
    # محاسبه قدرت
    attacker_power = (
        att_infantry * 1.0 +
        att_archer * 1.5 +
        att_cavalry * 2.0 +
        att_spearman * 1.2 +
        att_thief * 0.8
    )
    
    defender_power = (
        def_infantry * 1.0 +
        def_archer * 1.5 +
        def_cavalry * 2.0 +
        def_spearman * 1.2 +
        def_thief * 0.8 +
        def_wall * 0.5 +
        def_tower * 1.0 +
        def_gate * 0.8
    )
    
    # فاکتور شانس
    luck = random.uniform(0.8, 1.2)
    attacker_power *= luck
    
    result = {
        'attacker_infantry_loss': 0,
        'attacker_archer_loss': 0,
        'attacker_cavalry_loss': 0,
        'attacker_spearman_loss': 0,
        'attacker_thief_loss': 0,
        'defender_infantry_loss': 0,
        'defender_archer_loss': 0,
        'defender_cavalry_loss': 0,
        'defender_spearman_loss': 0,
        'defender_thief_loss': 0,
        'defense_wall_damage': 0,
        'defense_tower_damage': 0,
        'defense_gate_damage': 0,
        'gold_looted': 0,
        'iron_looted': 0,
        'food_looted': 0
    }
    
    if attacker_power > defender_power:
        # حمله موفق
        victory_ratio = (attacker_power - defender_power) / attacker_power
        result['result'] = "پیروزی"
        
        # تلفات مهاجم
        result['attacker_infantry_loss'] = int(att_infantry * (1 - victory_ratio) * 0.2)
        result['attacker_archer_loss'] = int(att_archer * (1 - victory_ratio) * 0.15)
        result['attacker_cavalry_loss'] = int(att_cavalry * (1 - victory_ratio) * 0.1)
        result['attacker_spearman_loss'] = int(att_spearman * (1 - victory_ratio) * 0.18)
        result['attacker_thief_loss'] = int(att_thief * (1 - victory_ratio) * 0.25)
        
        # تلفات مدافع
        result['defender_infantry_loss'] = int(def_infantry * victory_ratio * 0.7)
        result['defender_archer_loss'] = int(def_archer * victory_ratio * 0.6)
        result['defender_cavalry_loss'] = int(def_cavalry * victory_ratio * 0.5)
        result['defender_spearman_loss'] = int(def_spearman * victory_ratio * 0.65)
        result['defender_thief_loss'] = int(def_thief * victory_ratio * 0.8)
        
        # آسیب به دفاع
        result['defense_wall_damage'] = int(def_wall * victory_ratio * 0.4)
        result['defense_tower_damage'] = int(def_tower * victory_ratio * 0.3)
        result['defense_gate_damage'] = int(def_gate * victory_ratio * 0.5)
        
        # غنائم
        result['gold_looted'] = random.randint(100, 500)
        result['iron_looted'] = random.randint(50, 200)
        result['food_looted'] = random.randint(200, 800)
        
    else:
        # دفاع موفق
        defense_ratio = (defender_power - attacker_power) / defender_power
        result['result'] = "شکست"
        
        # تلفات مهاجم
        result['attacker_infantry_loss'] = int(att_infantry * defense_ratio * 0.6)
        result['attacker_archer_loss'] = int(att_archer * defense_ratio * 0.5)
        result['attacker_cavalry_loss'] = int(att_cavalry * defense_ratio * 0.4)
        result['attacker_spearman_loss'] = int(att_spearman * defense_ratio * 0.55)
        result['attacker_thief_loss'] = int(att_thief * defense_ratio * 0.7)
        
        # تلفات مدافع
        result['defender_infantry_loss'] = int(def_infantry * (1 - defense_ratio) * 0.15)
        result['defender_archer_loss'] = int(def_archer * (1 - defense_ratio) * 0.1)
        result['defender_cavalry_loss'] = int(def_cavalry * (1 - defense_ratio) * 0.05)
        result['defender_spearman_loss'] = int(def_spearman * (1 - defense_ratio) * 0.12)
        result['defender_thief_loss'] = int(def_thief * (1 - defense_ratio) * 0.2)
        
        # آسیب به دفاع
        result['defense_wall_damage'] = int(def_wall * (1 - defense_ratio) * 0.1)
        result['defense_tower_damage'] = int(def_tower * (1 - defense_ratio) * 0.05)
        result['defense_gate_damage'] = int(def_gate * (1 - defense_ratio) * 0.15)
        
        # غنائم
        result['gold_looted'] = random.randint(10, 50)
        result['iron_looted'] = random.randint(5, 20)
        result['food_looted'] = random.randint(20, 80)
    
    # محاسبه تلفات کل
    result['attacker_losses'] = sum([
        result['attacker_infantry_loss'],
        result['attacker_archer_loss'],
        result['attacker_cavalry_loss'],
        result['attacker_spearman_loss'],
        result['attacker_thief_loss']
    ])
    
    result['defender_losses'] = sum([
        result['defender_infantry_loss'],
        result['defender_archer_loss'],
        result['defender_cavalry_loss'],
        result['defender_spearman_loss'],
        result['defender_thief_loss']
    ])
    
    return result

# ========== منوها ==========
def main_menu(user_id):
    cursor = db_conn.cursor()
    cursor.execute('SELECT country FROM players WHERE user_id = ?', (user_id,))
    player = cursor.fetchone()
    has_country = player and player[0]
    
    keyboard = InlineKeyboardMarkup()
    
    if user_id == OWNER_ID:
        keyboard.row(
            InlineKeyboardButton("👑 افزودن بازیکن", callback_data="add_player"),
            InlineKeyboardButton("🌍 کشورها", callback_data="view_countries")
        )
        keyboard.row(
            InlineKeyboardButton("📊 منابع", callback_data="view_resources"),
            InlineKeyboardButton("⚔️ ارتش", callback_data="army_info")
        )
        keyboard.row(
            InlineKeyboardButton("🤝 دیپلماسی", callback_data="diplomacy"),
            InlineKeyboardButton("⛏️ معادن", callback_data="mines_farms")
        )
        keyboard.row(
            InlineKeyboardButton("▶️ شروع فصل", callback_data="start_season"),
            InlineKeyboardButton("⏹️ پایان فصل", callback_data="end_season")
        )
        keyboard.row(
            InlineKeyboardButton("🔄 ریست", callback_data="reset_game")
        )
    else:
        if has_country:
            keyboard.row(
                InlineKeyboardButton("🏛️ کشور من", callback_data="my_country"),
                InlineKeyboardButton("📊 منابع", callback_data="view_resources")
            )
            keyboard.row(
                InlineKeyboardButton("⚔️ ارتش", callback_data="army_info"),
                InlineKeyboardButton("🤝 دیپلماسی", callback_data="diplomacy")
            )
            keyboard.row(
                InlineKeyboardButton("⛏️ معادن", callback_data="mines_farms"),
                InlineKeyboardButton("🌍 کشورها", callback_data="view_countries")
            )
        else:
            keyboard.row(
                InlineKeyboardButton("🌍 مشاهده کشورها", callback_data="view_countries"),
                InlineKeyboardButton("📊 وضعیت من", callback_data="view_resources")
            )
    
    return keyboard

def army_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("👮 پیاده نظام", callback_data="army_infantry"),
        InlineKeyboardButton("🏹 کمانداران", callback_data="army_archer")
    )
    keyboard.row(
        InlineKeyboardButton("🐎 سوارهنظام", callback_data="army_cavalry"),
        InlineKeyboardButton("🗡️ نیزه‌داران", callback_data="army_spearman")
    )
    keyboard.row(
        InlineKeyboardButton("👤 دزدان", callback_data="army_thief"),
        InlineKeyboardButton("⚔️ حمله", callback_data="attack_country")
    )
    keyboard.row(
        InlineKeyboardButton("🏰 دفاع", callback_data="defend_borders"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")
    )
    return keyboard

def defense_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🧱 دیوار", callback_data="defense_wall"),
        InlineKeyboardButton("🏹 برج", callback_data="defense_tower")
    )
    keyboard.row(
        InlineKeyboardButton("🚪 دروازه", callback_data="defense_gate"),
        InlineKeyboardButton("🛡️ همه", callback_data="upgrade_all_defense")
    )
    keyboard.row(
        InlineKeyboardButton("🔙 بازگشت", callback_data="army_info")
    )
    return keyboard

def diplomacy_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🕊️ صلح", callback_data="peace_request"),
        InlineKeyboardButton("⚔️ جنگ", callback_data="declare_war")
    )
    keyboard.row(
        InlineKeyboardButton("🤝 اتحاد", callback_data="request_alliance"),
        InlineKeyboardButton("💰 تجارت", callback_data="trade_offer")
    )
    keyboard.row(
        InlineKeyboardButton("📜 پیشنهادها", callback_data="view_diplomacy_offers"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")
    )
    return keyboard

def mines_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("💰 طلا", callback_data="mine_gold"),
        InlineKeyboardButton("⚒️ آهن", callback_data="mine_iron")
    )
    keyboard.row(
        InlineKeyboardButton("🪨 سنگ", callback_data="mine_stone"),
        InlineKeyboardButton("🌾 غذا", callback_data="farm_food")
    )
    keyboard.row(
        InlineKeyboardButton("🏗️ سرباز", callback_data="barracks"),
        InlineKeyboardButton("📦 جمع‌آوری", callback_data="collect_resources")
    )
    keyboard.row(
        InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")
    )
    return keyboard

def countries_menu(only_free=False, user_id=None):
    keyboard = InlineKeyboardMarkup()
    cursor = db_conn.cursor()
    
    if only_free:
        cursor.execute('SELECT name FROM countries WHERE controller = "AI"')
    elif user_id:
        cursor.execute('SELECT name FROM countries WHERE controller = "HUMAN" AND player_id != ?', (user_id,))
    else:
        cursor.execute('SELECT name FROM countries')
    
    countries = cursor.fetchall()
    
    # ایجاد ردیف‌های 2 تایی
    for i in range(0, len(countries), 2):
        row = []
        if i < len(countries):
            row.append(InlineKeyboardButton(f"🏛️ {countries[i][0]}", callback_data=f"country_{countries[i][0]}"))
        if i + 1 < len(countries):
            row.append(InlineKeyboardButton(f"🏛️ {countries[i+1][0]}", callback_data=f"country_{countries[i+1][0]}"))
        if row:
            keyboard.row(*row)
    
    keyboard.row(InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu"))
    return keyboard

# ========== هندلرهای اصلی ==========
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # ثبت کاربر در دیتابیس
    cursor = db_conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO players (user_id, username, join_date, last_active) VALUES (?, ?, ?, ?)',
                  (user_id, username, datetime.now(), datetime.now()))
    db_conn.commit()
    
    welcome_text = f"""👋 سلام {message.from_user.first_name}!
به بازی جنگ جهانی باستان خوش آمدید.

🎮 شما: {'👑 مالک بازی' if user_id == OWNER_ID else '🎮 بازیکن'}

🏛️ مدیریت کشور باستانی خود
⚔️ ارتش‌های متنوع بسازید
🤝 با دیگران دیپلماسی کنید
⛏️ معادن را توسعه دهید

برای شروع از منوی زیر انتخاب کنید:"""
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(user_id))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    cursor = db_conn.cursor()
    
    # ========== منوی اصلی ==========
    if call.data == "main_menu":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"منوی اصلی\nشما: {'👑 مالک' if user_id == OWNER_ID else '🎮 بازیکن'}",
            reply_markup=main_menu(user_id)
        )
    
    # ========== کشور من ==========
    elif call.data == "my_country":
        cursor.execute('''
            SELECT c.name, c.special_resource, 
                   p.gold, p.iron, p.stone, p.food, p.wood,
                   p.army_infantry, p.army_archer, p.army_cavalry, 
                   p.army_spearman, p.army_thief,
                   p.defense_wall, p.defense_tower, p.defense_gate
            FROM players p
            LEFT JOIN countries c ON p.country = c.name
            WHERE p.user_id = ?
        ''', (user_id,))
        
        player_data = cursor.fetchone()
        
        if player_data and player_data[0]:
            name, resource, gold, iron, stone, food, wood, infantry, archer, cavalry, spearman, thief, wall, tower, gate = player_data
            
            # محاسبه قدرت
            player_dict = {
                'army_infantry': infantry,
                'army_archer': archer,
                'army_cavalry': cavalry,
                'army_spearman': spearman,
                'army_thief': thief,
                'defense_wall': wall,
                'defense_tower': tower,
                'defense_gate': gate
            }
            
            army_power = calculate_army_power(player_dict)
            defense_power = calculate_defense_power(player_dict)
            
            text = f"""🏛️ **کشور شما: {name}**

🎁 منبع ویژه: {resource}

💰 **ذخایر:**
• طلا: {gold}
• آهن: {iron}
• سنگ: {stone}
• غذا: {food}
• چوب: {wood}

👮 **ارتش:**
• پیاده نظام: {infantry}
• کمانداران: {archer}
• سوارهنظام: {cavalry}
• نیزه‌داران: {spearman}
• دزدان: {thief}

🛡️ **دفاع:**
• دیوار: {wall}
• برج نگهبانی: {tower}
• دروازه: {gate}

⚡ **قدرت کلی:**
• قدرت حمله: {army_power:.1f}
• قدرت دفاع: {defense_power:.1f}"""
        else:
            text = "⚠️ شما هنوز کشوری ندارید!\nلطفاً از مالک درخواست کشور کنید."
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    # ========== مشاهده کشورها ==========
    elif call.data == "view_countries":
        cursor.execute('''
            SELECT c.name, c.special_resource, c.controller, 
                   COALESCE(p.username, 'بدون بازیکن') as player_name,
                   p.army_infantry, p.army_archer, p.army_cavalry
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
        ''')
        
        countries = cursor.fetchall()
        
        text = "🌍 **لیست کشورهای باستانی:**\n\n"
        for name, resource, controller, player, infantry, archer, cavalry in countries:
            controller_icon = "🤖" if controller == "AI" else "👤"
            army_strength = ""
            if infantry and archer and cavalry:
                army_strength = f"👮 {infantry + archer + cavalry}"
            
            text += f"🏛️ **{name}**\n"
            text += f"   منبع ویژه: {resource}\n"
            text += f"   کنترل: {controller_icon} {player}\n"
            if army_strength:
                text += f"   قدرت نظامی: {army_strength}\n"
            text += f"   {'─'*20}\n"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    # ========== مشاهده منابع ==========
    elif call.data == "view_resources":
        cursor.execute('''
            SELECT p.gold, p.iron, p.stone, p.food, p.wood, c.name,
                   p.mine_gold_level, p.mine_iron_level, p.mine_stone_level, p.farm_level
            FROM players p
            LEFT JOIN countries c ON p.country = c.name
            WHERE p.user_id = ?
        ''', (user_id,))
        
        player = cursor.fetchone()
        
        if player:
            gold, iron, stone, food, wood, country, mine_gold, mine_iron, mine_stone, farm = player
            
            production = calculate_daily_production(user_id)
            
            text = f"""📊 **وضعیت منابع{' - ' + country if country else ''}**

💰 **ذخایر:**
• طلا: {gold}
• آهن: {iron}
• سنگ: {stone}
• غذا: {food}
• چوب: {wood}

🏭 **سطح تولیدکننده‌ها:**
• معدن طلا: سطح {mine_gold}
• معدن آهن: سطح {mine_iron}
• معدن سنگ: سطح {mine_stone}
• مزرعه: سطح {farm}

📈 **تولید روزانه:**
• طلا: {production['gold'] if production else 0}
• آهن: {production['iron'] if production else 0}
• سنگ: {production['stone'] if production else 0}
• غذا: {production['food'] if production else 0}
• چوب: {production['wood'] if production else 0}

💡 برای جمع‌آوری منابع به بخش معادن بروید."""
        else:
            text = "⚠️ شما هنوز ثبت‌نام نکرده‌اید."
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    # ========== بخش ارتش ==========
    elif call.data == "army_info":
        cursor.execute('''
            SELECT army_infantry, army_archer, army_cavalry, 
                   army_spearman, army_thief,
                   defense_wall, defense_tower, defense_gate,
                   country
            FROM players WHERE user_id = ?
        ''', (user_id,))
        
        player = cursor.fetchone()
        
        if player and player[8]:  # اگر کشور دارد
            infantry, archer, cavalry, spearman, thief, wall, tower, gate, country = player
            
            player_dict = {
                'army_infantry': infantry,
                'army_archer': archer,
                'army_cavalry': cavalry,
                'army_spearman': spearman,
                'army_thief': thief,
                'defense_wall': wall,
                'defense_tower': tower,
                'defense_gate': gate
            }
            
            army_power = calculate_army_power(player_dict)
            defense_power = calculate_defense_power(player_dict)
            
            text = f"""⚔️ **ارتش و جنگ - {country}**

👮 **نیروهای شما:**
• پیاده نظام: {infantry}
• کمانداران: {archer}
• سوارهنظام: {cavalry}
• نیزه‌داران: {spearman}
• دزدان: {thief}

🛡️ **سازه‌های دفاعی:**
• دیوار: {wall}
• برج نگهبانی: {tower}
• دروازه: {gate}

⚡ **قدرت کلی:**
• قدرت حمله: {army_power:.1f}
• قدرت دفاع: {defense_power:.1f}

از گزینه‌های زیر برای مدیریت ارتش استفاده کنید:"""
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=army_menu()
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ شما هنوز کشوری ندارید!",
                reply_markup=main_menu(user_id)
            )
    
    # ========== انواع سربازان ==========
    elif call.data in ["army_infantry", "army_archer", "army_cavalry", "army_spearman", "army_thief"]:
        army_types = {
            "army_infantry": {"name": "پیاده نظام", "cost_gold": 10, "cost_food": 20, "column": "army_infantry"},
            "army_archer": {"name": "کمانداران", "cost_gold": 15, "cost_food": 10, "column": "army_archer"},
            "army_cavalry": {"name": "سوارهنظام", "cost_gold": 30, "cost_food": 40, "column": "army_cavalry"},
            "army_spearman": {"name": "نیزه‌داران", "cost_gold": 12, "cost_food": 15, "column": "army_spearman"},
            "army_thief": {"name": "دزدان", "cost_gold": 5, "cost_food": 5, "column": "army_thief"}
        }
        
        army_info = army_types[call.data]
        
        cursor.execute('SELECT gold, food FROM players WHERE user_id = ?', (user_id,))
        resources = cursor.fetchone()
        
        if resources:
            gold, food = resources
            
            text = f"""👮 **{army_info['name']}**

💰 **هزینه استخدام:**
• هر 10 نفر: {army_info['cost_gold'] * 10} طلا + {army_info['cost_food'] * 10} غذا

💎 **منابع شما:**
• طلا: {gold}
• غذا: {food}

تعداد واحد (هر واحد = 10 سرباز) را وارد کنید:"""
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown'
            )
            
            # ثبت برای مرحله بعد
            bot.register_next_step_handler(call.message, lambda m: recruit_soldiers_step(m, army_info))
    
    # ========== حمله به کشور ==========
    elif call.data == "attack_country":
        cursor.execute('SELECT country FROM players WHERE user_id = ?', (user_id,))
        player = cursor.fetchone()
        
        if not player or not player[0]:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ شما کشوری ندارید که بتوانید حمله کنید!",
                reply_markup=main_menu(user_id)
            )
            return
        
        # نمایش کشورهای قابل حمله
        keyboard = InlineKeyboardMarkup()
        cursor.execute('''
            SELECT c.name, p.username, 
                   p.army_infantry + p.army_archer + p.army_cavalry as army_size
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
            WHERE c.controller = 'HUMAN' AND c.player_id != ?
            ORDER BY army_size
        ''', (user_id,))
        
        targets = cursor.fetchall()
        
        if targets:
            for name, target_player, army_size in targets:
                keyboard.row(InlineKeyboardButton(
                    f"⚔️ {name} ({target_player}) 👮{army_size}",
                    callback_data=f"attack_{name}"
                ))
            keyboard.row(InlineKeyboardButton("🔙 بازگشت", callback_data="army_info"))
            
            text = "⚔️ **حمله به کشورهای دیگر**\n\nکشورهای قابل حمله:"
        else:
            text = "⚠️ هیچ کشور انسانی دیگری برای حمله وجود ندارد!"
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("🔙 بازگشت", callback_data="army_info"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    # ========== اجرای حمله ==========
    elif call.data.startswith("attack_"):
        target_country = call.data.replace("attack_", "")
        
        # اطلاعات مهاجم
        cursor.execute('''
            SELECT p.army_infantry, p.army_archer, p.army_cavalry,
                   p.army_spearman, p.army_thief, c.name
            FROM players p
            LEFT JOIN countries c ON p.country = c.name
            WHERE p.user_id = ?
        ''', (user_id,))
        
        attacker = cursor.fetchone()
        
        if not attacker or not attacker[5]:
            bot.answer_callback_query(call.id, "⚠️ شما کشوری ندارید!")
            return
        
        attacker_army = attacker[:5]
        attacker_country = attacker[5]
        
        # اطلاعات مدافع
        cursor.execute('''
            SELECT p.user_id, p.army_infantry, p.army_archer, p.army_cavalry,
                   p.army_spearman, p.army_thief,
                   p.defense_wall, p.defense_tower, p.defense_gate,
                   p.gold, p.iron, p.food, p.username
            FROM players p
            LEFT JOIN countries c ON p.country = c.name
            WHERE c.name = ?
        ''', (target_country,))
        
        defender = cursor.fetchone()
        
        if not defender:
            bot.answer_callback_query(call.id, "⚠️ کشور یافت نشد!")
            return
        
        defender_id, defender_army, defender_defense = defender[0], defender[1:6], defender[6:9]
        defender_gold, defender_iron, defender_food, defender_username = defender[9:13]
        
        # شبیه‌سازی نبرد
        battle_result = simulate_battle(attacker_army, defender_army + defender_defense)
        
        # ذخیره نبرد
        attacker_losses_str = f"{battle_result['attacker_infantry_loss']}-{battle_result['attacker_archer_loss']}-{battle_result['attacker_cavalry_loss']}"
        defender_losses_str = f"{battle_result['defender_infantry_loss']}-{battle_result['defender_archer_loss']}-{battle_result['defender_cavalry_loss']}"
        
        cursor.execute('''
            INSERT INTO battles (attacker_id, defender_id, attacker_country, defender_country,
                               result, attacker_losses, defender_losses,
                               gold_looted, iron_looted, food_looted, battle_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, defender_id, attacker_country, target_country,
            battle_result['result'], attacker_losses_str, defender_losses_str,
            battle_result['gold_looted'], battle_result['iron_looted'], 
            battle_result['food_looted'], datetime.now()
        ))
        
        # آپدیت نیروهای مهاجم
        cursor.execute(f'''
            UPDATE players 
            SET army_infantry = army_infantry - ?,
                army_archer = army_archer - ?,
                army_cavalry = army_cavalry - ?,
                army_spearman = army_spearman - ?,
                army_thief = army_thief - ?,
                gold = gold + ?,
                iron = iron + ?,
                food = food + ?
            WHERE user_id = ?
        ''', (
            battle_result['attacker_infantry_loss'],
            battle_result['attacker_archer_loss'],
            battle_result['attacker_cavalry_loss'],
            battle_result['attacker_spearman_loss'],
            battle_result['attacker_thief_loss'],
            battle_result['gold_looted'],
            battle_result['iron_looted'],
            battle_result['food_looted'],
            user_id
        ))
        
        # آپدیت نیروهای مدافع
        cursor.execute(f'''
            UPDATE players 
            SET army_infantry = army_infantry - ?,
                army_archer = army_archer - ?,
                army_cavalry = army_cavalry - ?,
                army_spearman = army_spearman - ?,
                army_thief = army_thief - ?,
                defense_wall = defense_wall - ?,
                defense_tower = defense_tower - ?,
                defense_gate = defense_gate - ?,
                gold = gold - ?,
                iron = iron - ?,
                food = food - ?
            WHERE user_id = ?
        ''', (
            battle_result['defender_infantry_loss'],
            battle_result['defender_archer_loss'],
            battle_result['defender_cavalry_loss'],
            battle_result['defender_spearman_loss'],
            battle_result['defender_thief_loss'],
            battle_result['defense_wall_damage'],
            battle_result['defense_tower_damage'],
            battle_result['defense_gate_damage'],
            min(battle_result['gold_looted'], defender_gold),
            min(battle_result['iron_looted'], defender_iron),
            min(battle_result['food_looted'], defender_food),
            defender_id
        ))
        
        db_conn.commit()
        
        # نمایش نتیجه
        text = f"""⚔️ **نتیجه نبرد با {target_country}**

🏆 **{battle_result['result']}**

📊 **تلفات شما:**
• پیاده نظام: {battle_result['attacker_infantry_loss']}
• کمانداران: {battle_result['attacker_archer_loss']}
• سوارهنظام: {battle_result['attacker_cavalry_loss']}
• نیزه‌داران: {battle_result['attacker_spearman_loss']}
• دزدان: {battle_result['attacker_thief_loss']}

📊 **تلفات دشمن:**
• پیاده نظام: {battle_result['defender_infantry_loss']}
• کمانداران: {battle_result['defender_archer_loss']}
• سوارهنظام: {battle_result['defender_cavalry_loss']}
• نیزه‌داران: {battle_result['defender_spearman_loss']}
• دزدان: {battle_result['defender_thief_loss']}

🛡️ **آسیب به دفاع دشمن:**
• دیوار: {battle_result['defense_wall_damage']}
• برج: {battle_result['defense_tower_damage']}
• دروازه: {battle_result['defense_gate_damage']}

💰 **غنائم:**
• طلا: {battle_result['gold_looted']}
• آهن: {battle_result['iron_looted']}
• غذا: {battle_result['food_looted']}"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
        
        # اطلاع به مدافع
        try:
            bot.send_message(
                defender_id,
                f"""⚠️ **حمله به کشور شما!**

🏛️ کشور شما ({target_country}) مورد حمله قرار گرفت!

⚔️ **مهاجم:** {attacker_country}
🏆 **نتیجه:** {battle_result['result']}

برای جزئیات بیشتر به بازی مراجعه کنید."""
            )
        except:
            pass
    
    # ========== دفاع از مرز ==========
    elif call.data == "defend_borders":
        cursor.execute('''
            SELECT defense_wall, defense_tower, defense_gate,
                   gold, stone, iron, food, wood
            FROM players WHERE user_id = ?
        ''', (user_id,))
        
        player = cursor.fetchone()
        
        if player:
            wall, tower, gate, gold, stone, iron, food, wood = player
            
            text = f"""🏰 **دفاع از مرزها**

🛡️ **وضعیت فعلی دفاع:**
• دیوار: {wall}
• برج نگهبانی: {tower}
• دروازه: {gate}

💰 **منابع شما:**
• طلا: {gold}
• سنگ: {stone}
• آهن: {iron}
• غذا: {food}
• چوب: {wood}

🛠️ **هزینه تقویت هر واحد:**
• دیوار: 20 سنگ + 10 طلا
• برج: 30 سنگ + 20 آهن + 15 طلا
• دروازه: 25 سنگ + 15 آهن + 10 طلا"""
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=defense_menu()
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ شما هنوز کشوری ندارید!",
                reply_markup=main_menu(user_id)
            )
    
    # ========== تقویت دفاع ==========
    elif call.data in ["defense_wall", "defense_tower", "defense_gate"]:
        defense_types = {
            "defense_wall": {"name": "دیوار", "cost_stone": 20, "cost_gold": 10, "column": "defense_wall"},
            "defense_tower": {"name": "برج نگهبانی", "cost_stone": 30, "cost_iron": 20, "cost_gold": 15, "column": "defense_tower"},
            "defense_gate": {"name": "دروازه", "cost_stone": 25, "cost_iron": 15, "cost_gold": 10, "column": "defense_gate"}
        }
        
        defense_info = defense_types[call.data]
        
        cursor.execute('SELECT gold, stone, iron FROM players WHERE user_id = ?', (user_id,))
        resources = cursor.fetchone()
        
        if resources:
            gold, stone, iron = resources
            
            costs = []
            if 'cost_gold' in defense_info:
                costs.append(f"💰 طلا: {defense_info['cost_gold']}")
            if 'cost_stone' in defense_info:
                costs.append(f"🪨 سنگ: {defense_info['cost_stone']}")
            if 'cost_iron' in defense_info:
                costs.append(f"⚒️ آهن: {defense_info['cost_iron']}")
            
            text = f"""🛡️ **تقویت {defense_info['name']}**

📋 **هزینه تقویت هر واحد:**
{chr(10).join(costs)}

💎 **منابع شما:**
• طلا: {gold}
• سنگ: {stone}
• آهن: {iron}

تعداد واحد مورد نظر برای تقویت را وارد کنید:"""
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown'
            )
            
            # ثبت برای مرحله بعد
            bot.register_next_step_handler(call.message, lambda m: upgrade_defense_step(m, defense_info))
    
    # ========== دیپلماسی ==========
    elif call.data == "diplomacy":
        cursor.execute('SELECT country FROM players WHERE user_id = ?', (user_id,))
        player = cursor.fetchone()
        
        if not player or not player[0]:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ شما کشوری ندارید!",
                reply_markup=main_menu(user_id)
            )
            return
        
        text = """🤝 **دیپلماسی**

از طریق دیپلماسی می‌توانید با دیگر کشورها:
• درخواست صلح کنید
• اعلام جنگ دهید
• درخواست اتحاد کنید
• پیشنهاد تجارت دهید

پیشنهادهای دریافتی خود را نیز می‌توانید مشاهده و پاسخ دهید.

لطفاً گزینه مورد نظر را انتخاب کنید:"""
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=diplomacy_menu()
        )
    
    # ========== اقدامات دیپلماتیک ==========
    elif call.data in ["peace_request", "declare_war", "request_alliance", "trade_offer"]:
        actions = {
            "peace_request": {"name": "درخواست صلح", "emoji": "🕊️", "cost": 100},
            "declare_war": {"name": "اعلام جنگ", "emoji": "⚔️", "cost": 0},
            "request_alliance": {"name": "درخواست اتحاد", "emoji": "🤝", "cost": 200},
            "trade_offer": {"name": "پیشنهاد تجارت", "emoji": "💰", "cost": 50}
        }
        
        action_info = actions[call.data]
        
        # نمایش کشورهای هدف
        keyboard = InlineKeyboardMarkup()
        cursor.execute('''
            SELECT c.name, p.username
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
            WHERE c.controller = 'HUMAN' AND c.player_id != ?
        ''', (user_id,))
        
        targets = cursor.fetchall()
        
        if targets:
            for name, target_player in targets:
                keyboard.row(InlineKeyboardButton(
                    f"{action_info['emoji']} {name} ({target_player})",
                    callback_data=f"diplo_{call.data}_{name}"
                ))
            keyboard.row(InlineKeyboardButton("🔙 بازگشت", callback_data="diplomacy"))
            
            cost_text = f"\n💰 هزینه: {action_info['cost']} طلا" if action_info['cost'] > 0 else ""
            
            text = f"""{action_info['emoji']} **{action_info['name']}**

کشور مورد نظر را انتخاب کنید:{cost_text}"""
        else:
            text = "⚠️ هیچ کشور انسانی دیگری برای ارتباط وجود ندارد!"
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("🔙 بازگشت", callback_data="diplomacy"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    # ========== ارسال درخواست دیپلماسی ==========
    elif call.data.startswith("diplo_"):
        parts = call.data.split("_")
        if len(parts) >= 3:
            action = parts[1]
            target_country = "_".join(parts[2:])
            
            actions_info = {
                "peace": {"name": "درخواست صلح", "cost": 100},
                "war": {"name": "اعلام جنگ", "cost": 0},
                "alliance": {"name": "درخواست اتحاد", "cost": 200},
                "trade": {"name": "پیشنهاد تجارت", "cost": 50}
            }
            
            # گرفتن کشور فرستنده
            cursor.execute('SELECT country FROM players WHERE user_id = ?', (user_id,))
            from_country_result = cursor.fetchone()
            
            if not from_country_result or not from_country_result[0]:
                bot.answer_callback_query(call.id, "⚠️ شما کشوری ندارید!")
                return
            
            from_country = from_country_result[0]
            
            # گرفتن ID مدافع
            cursor.execute('SELECT player_id FROM countries WHERE name = ?', (target_country,))
            target_result = cursor.fetchone()
            
            if not target_result or not target_result[0]:
                bot.answer_callback_query(call.id, "⚠️ کشور هدف بازیکن ندارد!")
                return
            
            to_player_id = target_result[0]
            
            # بررسی هزینه
            if action in actions_info:
                cost = actions_info[action]["cost"]
                if cost > 0:
                    cursor.execute('SELECT gold FROM players WHERE user_id = ?', (user_id,))
                    gold_result = cursor.fetchone()
                    if gold_result and gold_result[0] < cost:
                        bot.answer_callback_query(call.id, f"⚠️ طلای کافی ندارید! نیاز: {cost}")
                        return
                    
                    # کسر طلا
                    cursor.execute('UPDATE players SET gold = gold - ? WHERE user_id = ?', (cost, user_id))
            
            # ثبت درخواست
            cursor.execute('''
                INSERT INTO diplomacy (from_player_id, to_player_id, from_country, to_country,
                                     relation_type, message, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                to_player_id,
                from_country,
                target_country,
                action,
                f"{actions_info[action]['name']} از {from_country}",
                datetime.now(),
                datetime.now()
            ))
            db_conn.commit()
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"""✅ **درخواست ارسال شد!**

🏛️ به کشور: {target_country}
📋 نوع: {actions_info[action]['name']}
⏰ وضعیت: در انتظار پاسخ

منتظر پاسخ باشید.""",
                parse_mode='Markdown',
                reply_markup=main_menu(user_id)
            )
            
            # اطلاع به مدافع
            try:
                bot.send_message(
                    to_player_id,
                    f"""📩 **درخواست دیپلماسی جدید!**

🏛️ از کشور: {from_country}
📋 نوع: {actions_info[action]['name']}

برای مشاهده و پاسخ به منوی دیپلماسی → مشاهده پیشنهادها بروید."""
                )
            except:
                pass
    
    # ========== مشاهده پیشنهادهای دیپلماسی ==========
    elif call.data == "view_diplomacy_offers":
        cursor.execute('''
            SELECT d.id, d.relation_type, d.message, d.created_at,
                   d.from_country, p.username as from_player
            FROM diplomacy d
            LEFT JOIN players p ON d.from_player_id = p.user_id
            WHERE d.to_player_id = ? AND d.status = 'pending'
            ORDER BY d.created_at DESC
            LIMIT 10
        ''', (user_id,))
        
        offers = cursor.fetchall()
        
        if offers:
            text = "📜 **پیشنهادهای دیپلماسی دریافتی:**\n\n"
            
            keyboard = InlineKeyboardMarkup()
            
            for i, offer in enumerate(offers, 1):
                offer_id, relation_type, message, created_at, from_country, from_player = offer
                
                relation_names = {
                    "peace": "🕊️ صلح",
                    "war": "⚔️ جنگ",
                    "alliance": "🤝 اتحاد",
                    "trade": "💰 تجارت"
                }
                
                relation_text = relation_names.get(relation_type, relation_type)
                text += f"{i}. {relation_text}\n"
                text += f"   از: {from_country} ({from_player})\n"
                text += f"   زمان: {created_at[:16]}\n"
                text += f"   {'─'*20}\n"
                
                # دکمه‌های پاسخ
                keyboard.row(
                    InlineKeyboardButton(f"✅ {i}", callback_data=f"diplo_accept_{offer_id}"),
                    InlineKeyboardButton(f"❌ {i}", callback_data=f"diplo_reject_{offer_id}")
                )
            
            text += "\nبرای پاسخ به هر پیشنهاد، دکمه مربوطه را انتخاب کنید."
            keyboard.row(InlineKeyboardButton("🔙 بازگشت", callback_data="diplomacy"))
            
        else:
            text = "📭 **هیچ پیشنهاد دیپلماسی جدیدی ندارید.**"
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("🔙 بازگشت", callback_data="diplomacy"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    # ========== پاسخ به دیپلماسی ==========
    elif call.data.startswith("diplo_accept_") or call.data.startswith("diplo_reject_"):
        parts = call.data.split("_")
        action = parts[1]  # accept یا reject
        offer_id = parts[2]
        
        # گرفتن اطلاعات پیشنهاد
        cursor.execute('''
            SELECT d.relation_type, d.from_player_id, d.from_country, d.message
            FROM diplomacy d
            WHERE d.id = ? AND d.to_player_id = ?
        ''', (offer_id, user_id))
        
        offer = cursor.fetchone()
        
        if offer:
            relation_type, from_player_id, from_country, message = offer
            
            # آپدیت وضعیت
            cursor.execute('UPDATE diplomacy SET status = ? WHERE id = ?', (action, offer_id))
            db_conn.commit()
            
            relation_names = {
                "peace": "صلح",
                "war": "جنگ",
                "alliance": "اتحاد",
                "trade": "تجارت"
            }
            
            action_texts = {
                "accept": "✅ پذیرفته شد",
                "reject": "❌ رد شد"
            }
            
            # اطلاع به فرستنده
            try:
                bot.send_message(
                    from_player_id,
                    f"""📨 **پاسخ به درخواست دیپلماسی**

🏛️ کشور شما: {from_country}
📋 درخواست: {relation_names.get(relation_type, relation_type)}
📝 وضعیت: {action_texts.get(action, action)}

پاسخ به درخواست شما ثبت شد."""
                )
            except:
                pass
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"""📨 **پاسخ ثبت شد**

{action_texts.get(action, action)}

درخواست شما با موفقیت ثبت شد.""",
                parse_mode='Markdown',
                reply_markup=main_menu(user_id)
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⚠️ پیشنهاد یافت نشد!",
                reply_markup=main_menu(user_id)
            )
    
    # ========== معادن و مزارع ==========
    elif call.data == "mines_farms":
        cursor.execute('''
            SELECT mine_gold_level, mine_iron_level, mine_stone_level,
                   farm_level, barracks_level, country,
                   gold, iron, stone, food, wood
            FROM players WHERE user_id = ?
        ''', (user_id,))
        
        player = cursor.fetchone()
        
        if player:
            mine_gold, mine_iron, mine_stone, farm, barracks, country, gold, iron, stone, food, wood = player
            
            production = calculate_daily_production(user_id)
            
            text = f"""⛏️ **معادن و مزارع{' - ' + country if country else ''}**

🏭 **سطح سازه‌های شما:**
💰 معدن طلا: سطح {mine_gold} (تولید: {production['gold'] if production else 0}/روز)
⚒️ معدن آهن: سطح {mine_iron} (تولید: {production['iron'] if production else 0}/روز)
🪨 معدن سنگ: سطح {mine_stone} (تولید: {production['stone'] if production else 0}/روز)
🌾 مزرعه غذا: سطح {farm} (تولید: {production['food'] if production else 0}/روز)
🏗️ کارخانه سرباز: سطح {barracks}

📦 **منابع ذخیره شده:**
• طلا: {gold}
• آهن: {iron}
• سنگ: {stone}
• غذا: {food}
• چوب: {wood}

💡 برای ارتقاء سازه‌ها یا جمع‌آوری منابع گزینه مورد نظر را انتخاب کنید:"""
        else:
            text = "⚠️ شما هنوز کشوری ندارید!"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=mines_menu()
        )
    
    # ========== انواع معادن ==========
    elif call.data in ["mine_gold", "mine_iron", "mine_stone", "farm_food", "barracks"]:
        mine_types = {
            "mine_gold": {"name": "معدن طلا", "resource": "gold", "column": "mine_gold_level", 
                          "cost_stone": 100, "cost_wood": 50},
            "mine_iron": {"name": "معدن آهن", "resource": "iron", "column": "mine_iron_level", 
                          "cost_stone": 80, "cost_wood": 60},
            "mine_stone": {"name": "معدن سنگ", "resource": "stone", "column": "mine_stone_level", 
                           "cost_stone": 50, "cost_wood": 70},
            "farm_food": {"name": "مزرعه غذا", "resource": "food", "column": "farm_level", 
                          "cost_wood": 100, "cost_gold": 30},
            "barracks": {"name": "کارخانه سرباز", "resource": "training", "column": "barracks_level", 
                         "cost_stone": 200, "cost_wood": 150, "cost_gold": 100}
        }
        
        mine_info = mine_types[call.data]
        
        cursor.execute('SELECT stone, wood, gold FROM players WHERE user_id = ?', (user_id,))
        resources = cursor.fetchone()
        
        if resources:
            stone, wood, gold = resources
            
            # گرفتن سطح فعلی
            cursor.execute(f'SELECT {mine_info["column"]} FROM players WHERE user_id = ?', (user_id,))
            current_level = cursor.fetchone()[0]
            
            costs = []
            if 'cost_stone' in mine_info:
                costs.append(f"🪨 سنگ: {mine_info['cost_stone']}")
            if 'cost_wood' in mine_info:
                costs.append(f"🌲 چوب: {mine_info['cost_wood']}")
            if 'cost_gold' in mine_info:
                costs.append(f"💰 طلا: {mine_info['cost_gold']}")
            
            text = f"""🏭 **{mine_info['name']}**

📊 **وضعیت فعلی:**
• سطح: {current_level}

🛠️ **هزینه ارتقاء به سطح {current_level + 1}:**
{chr(10).join(costs)}

💎 **منابع شما:**
• سنگ: {stone}
• چوب: {wood}
• طلا: {gold}

آیا می‌خواهید این سازه را ارتقاء دهید؟"""

            keyboard = InlineKeyboardMarkup()
            keyboard.row(
                InlineKeyboardButton("✅ بله، ارتقاء بده", callback_data=f"upgrade_{call.data}"),
                InlineKeyboardButton("❌ خیر", callback_data="mines_farms")
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    
    # ========== ارتقاء معدن ==========
    elif call.data.startswith("upgrade_"):
        mine_type = call.data.replace("upgrade_", "")
        mine_types = {
            "mine_gold": {"column": "mine_gold_level", "cost_stone": 100, "cost_wood": 50},
            "mine_iron": {"column": "mine_iron_level", "cost_stone": 80, "cost_wood": 60},
            "mine_stone": {"column": "mine_stone_level", "cost_stone": 50, "cost_wood": 70},
            "farm_food": {"column": "farm_level", "cost_wood": 100, "cost_gold": 30},
            "barracks": {"column": "barracks_level", "cost_stone": 200, "cost_wood": 150, "cost_gold": 100}
        }
        
        if mine_type in mine_types:
            mine_info = mine_types[mine_type]
            
            cursor.execute('SELECT stone, wood, gold FROM players WHERE user_id = ?', (user_id,))
            resources = cursor.fetchone()
            
            if resources:
                stone, wood, gold = resources
                can_upgrade = True
                missing_resources = []
                
                # بررسی منابع
                if 'cost_stone' in mine_info and stone < mine_info['cost_stone']:
                    can_upgrade = False
                    missing_resources.append(f"سنگ (نیاز: {mine_info['cost_stone']}, موجود: {stone})")
                if 'cost_wood' in mine_info and wood < mine_info['cost_wood']:
                    can_upgrade = False
                    missing_resources.append(f"چوب (نیاز: {mine_info['cost_wood']}, موجود: {wood})")
                if 'cost_gold' in mine_info and gold < mine_info['cost_gold']:
                    can_upgrade = False
                    missing_resources.append(f"طلا (نیاز: {mine_info['cost_gold']}, موجود: {gold})")
                
                if can_upgrade:
                    # ساخت کوئری آپدیت
                    set_clauses = []
                    values = []
                    
                    if 'cost_stone' in mine_info:
                        set_clauses.append("stone = stone - ?")
                        values.append(mine_info['cost_stone'])
                    if 'cost_wood' in mine_info:
                        set_clauses.append("wood = wood - ?")
                        values.append(mine_info['cost_wood'])
                    if 'cost_gold' in mine_info:
                        set_clauses.append("gold = gold - ?")
                        values.append(mine_info['cost_gold'])
                    
                    set_clauses.append(f"{mine_info['column']} = {mine_info['column']} + 1")
                    values.append(user_id)
                    
                    update_query = f"UPDATE players SET {', '.join(set_clauses)} WHERE user_id = ?"
                    cursor.execute(update_query, values)
                    db_conn.commit()
                    
                    text = "✅ سازه با موفقیت ارتقاء یافت!"
                else:
                    text = f"❌ منابع کافی نیست!\n\nمنابع مورد نیاز:\n{chr(10).join(missing_resources)}"
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=mines_menu()
                )
    
    # ========== جمع‌آوری منابع ==========
    elif call.data == "collect_resources":
        production = calculate_daily_production(user_id)
        
        if production:
            # افزودن منابع
            cursor.execute('''
                UPDATE players 
                SET gold = gold + ?, 
                    iron = iron + ?, 
                    stone = stone + ?, 
                    food = food + ?,
                    wood = wood + ?,
                    last_active = ?
                WHERE user_id = ?
            ''', (
                production['gold'],
                production['iron'],
                production['stone'],
                production['food'],
                production['wood'],
                datetime.now(),
                user_id
            ))
            db_conn.commit()
            
            text = f"""📦 **منابع جمع‌آوری شد!**

💰 طلا: +{production['gold']}
⚒️ آهن: +{production['iron']}
🪨 سنگ: +{production['stone']}
🍖 غذا: +{production['food']}
🌲 چوب: +{production['wood']}

منابع به حساب شما اضافه شدند."""
        else:
            text = "⚠️ خطا در محاسبه تولید!"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=mines_menu()
        )
    
    # ========== افزودن بازیکن (مالک) ==========
    elif call.data == "add_player":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔ دسترسی ممنوع!")
            return
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🏛️ انتخاب کشور برای بازیکن جدید:\n\nکشورهای آزاد:",
            reply_markup=countries_menu(only_free=True)
        )
    
    # ========== انتخاب کشور برای بازیکن جدید ==========
    elif call.data.startswith("country_"):
        country_name = call.data.replace("country_", "")
        
        if user_id == OWNER_ID:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"کشور '{country_name}' انتخاب شد.\n\nلطفاً آیدی عددی کاربر را ارسال کنید:"
            )
            bot.register_next_step_handler(call.message, lambda m: add_player_step(m, country_name))
    
    # ========== شروع فصل ==========
    elif call.data == "start_season":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔ دسترسی ممنوع!")
            return
        
        try:
            # ارسال به کانال
            bot.send_message(
                CHANNEL_ID,
                "🎉 **شروع فصل جدید جنگ‌های باستان!**\n\n"
                "جهان باستان زنده شد! کشورها برای فتح جهان آماده می‌شوند...\n\n"
                "ساخته شده توسط @amele55\n"
                "ورژن 2 ربات - با سیستم‌های کامل"
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
    
    # ========== پایان فصل ==========
    elif call.data == "end_season":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "⛔ دسترسی ممنوع!")
            return
        
        try:
            # پیدا کردن برنده
            cursor.execute('''
                SELECT p.user_id, p.username, c.name, 
                       (p.gold + p.iron * 2 + p.stone * 1.5 + p.food + 
                        (p.army_infantry + p.army_archer + p.army_cavalry) * 10) as score
                FROM players p
                LEFT JOIN countries c ON p.country = c.name
                WHERE c.controller = 'HUMAN' AND p.country IS NOT NULL
                ORDER BY score DESC
                LIMIT 1
            ''')
            
            winner = cursor.fetchone()
            
            if winner:
                user_id_winner, username, country, score = winner
                
                # ارسال به کانال
                bot.send_message(
                    CHANNEL_ID,
                    f"""🏆 **پایان فصل جنگ‌های باستان**

👑 فاتح نهایی جهان:
🏛️ **{country}**

👤 بازیکن: {username} (ID: {user_id_winner})
📊 امتیاز: {score}

ساخته شده توسط @amele55
منتظر فصل بعد باشید
ورژن 2 ربات"""
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
    
    # ========== ریست بازی ==========
    elif call.data == "reset_game":
        if user_id != OWNER_ID:
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
        if user_id != OWNER_ID:
            return
        
        try:
            cursor = db_conn.cursor()
            # ریست بازیکنان
            cursor.execute('''
                UPDATE players 
                SET country = NULL, 
                    gold = 1000, iron = 500, stone = 500, food = 1000, wood = 500,
                    army_infantry = 50, army_archer = 30, army_cavalry = 20,
                    army_spearman = 40, army_thief = 10,
                    defense_wall = 50, defense_tower = 20, defense_gate = 30,
                    mine_gold_level = 1, mine_iron_level = 1, mine_stone_level = 1,
                    farm_level = 1, barracks_level = 1
            ''')
            # ریست کشورها
            cursor.execute('UPDATE countries SET controller = "AI", player_id = NULL')
            # پاک کردن جدول‌های دیگر
            cursor.execute('DELETE FROM battles')
            cursor.execute('DELETE FROM diplomacy')
            cursor.execute('DELETE FROM mines')
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

# ========== توابع مرحله‌ای ==========
def recruit_soldiers_step(message, army_info):
    user_id = message.from_user.id
    
    try:
        amount = int(message.text)
        if amount <= 0:
            bot.reply_to(message, "⚠️ تعداد باید بیشتر از 0 باشد!")
            return
        
        cursor = db_conn.cursor()
        
        # بررسی منابع
        cursor.execute('SELECT gold, food FROM players WHERE user_id = ?', (user_id,))
        resources = cursor.fetchone()
        
        if resources:
            gold, food = resources
            unit_count = amount * 10  # هر واحد = 10 سرباز
            total_gold_cost = army_info['cost_gold'] * unit_count
            total_food_cost = army_info['cost_food'] * unit_count
            
            if gold >= total_gold_cost and food >= total_food_cost:
                # کسر منابع و افزایش نیرو
                cursor.execute(f'''
                    UPDATE players 
                    SET gold = gold - ?, 
                        food = food - ?,
                        {army_info['column']} = {army_info['column']} + ?
                    WHERE user_id = ?
                ''', (total_gold_cost, total_food_cost, unit_count, user_id))
                db_conn.commit()
                
                bot.reply_to(
                    message,
                    f"""✅ استخدام موفق!

👮 {unit_count} نفر {army_info['name']} استخدام شدند.

💰 هزینه‌ها:
• طلا: {total_gold_cost}
• غذا: {total_food_cost}

نیروهای شما تقویت شدند.""",
                    reply_markup=main_menu(user_id)
                )
            else:
                missing = []
                if gold < total_gold_cost:
                    missing.append(f"طلا (نیاز: {total_gold_cost}, موجود: {gold})")
                if food < total_food_cost:
                    missing.append(f"غذا (نیاز: {total_food_cost}, موجود: {food})")
                
                bot.reply_to(
                    message,
                    f"❌ منابع کافی نیست!\n\nمنابع مورد نیاز:\n{chr(10).join(missing)}",
                    reply_markup=main_menu(user_id)
                )
    except ValueError:
        bot.reply_to(message, "⚠️ لطفاً یک عدد معتبر وارد کنید!")

def upgrade_defense_step(message, defense_info):
    user_id = message.from_user.id
    
    try:
        amount = int(message.text)
        if amount <= 0:
            bot.reply_to(message, "⚠️ تعداد باید بیشتر از 0 باشد!")
            return
        
        cursor = db_conn.cursor()
        
        # بررسی منابع
        cursor.execute('SELECT gold, stone, iron FROM players WHERE user_id = ?', (user_id,))
        resources = cursor.fetchone()
        
        if resources:
            gold, stone, iron = resources
            
            # محاسبه هزینه کل
            total_costs = {}
            missing_resources = []
            can_upgrade = True
            
            if 'cost_gold' in defense_info:
                total_costs['gold'] = defense_info['cost_gold'] * amount
                if gold < total_costs['gold']:
                    can_upgrade = False
                    missing_resources.append(f"طلا (نیاز: {total_costs['gold']}, موجود: {gold})")
            
            if 'cost_stone' in defense_info:
                total_costs['stone'] = defense_info['cost_stone'] * amount
                if stone < total_costs['stone']:
                    can_upgrade = False
                    missing_resources.append(f"سنگ (نیاز: {total_costs['stone']}, موجود: {stone})")
            
            if 'cost_iron' in defense_info:
                total_costs['iron'] = defense_info['cost_iron'] * amount
                if iron < total_costs['iron']:
                    can_upgrade = False
                    missing_resources.append(f"آهن (نیاز: {total_costs['iron']}, موجود: {iron})")
            
            if can_upgrade:
                # ساخت کوئری آپدیت
                set_clauses = []
                values = []
                
                if 'gold' in total_costs:
                    set_clauses.append("gold = gold - ?")
                    values.append(total_costs['gold'])
                
                if 'stone' in total_costs:
                    set_clauses.append("stone = stone - ?")
                    values.append(total_costs['stone'])
                
                if 'iron' in total_costs:
                    set_clauses.append("iron = iron - ?")
                    values.append(total_costs['iron'])
                
                set_clauses.append(f"{defense_info['column']} = {defense_info['column']} + ?")
                values.append(amount)
                values.append(user_id)
                
                update_query = f"UPDATE players SET {', '.join(set_clauses)} WHERE user_id = ?"
                cursor.execute(update_query, values)
                db_conn.commit()
                
                cost_text = []
                if 'gold' in total_costs:
                    cost_text.append(f"💰 طلا: {total_costs['gold']}")
                if 'stone' in total_costs:
                    cost_text.append(f"🪨 سنگ: {total_costs['stone']}")
                if 'iron' in total_costs:
                    cost_text.append(f"⚒️ آهن: {total_costs['iron']}")
                
                bot.reply_to(
                    message,
                    f"""✅ تقویت موفق!

🛡️ {amount} واحد {defense_info['name']} تقویت شد.

📋 هزینه‌ها:
{chr(10).join(cost_text)}

دفاع شما تقویت شد.""",
                    reply_markup=main_menu(user_id)
                )
            else:
                bot.reply_to(
                    message,
                    f"❌ منابع کافی نیست!\n\nمنابع مورد نیاز:\n{chr(10).join(missing_resources)}",
                    reply_markup=main_menu(user_id)
                )
    except ValueError:
        bot.reply_to(message, "⚠️ لطفاً یک عدد معتبر وارد کنید!")

def add_player_step(message, country_name):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.reply_to(message, "⛔ دسترسی ممنوع!")
        return
    
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
            cursor.execute('INSERT INTO players (user_id, country, join_date, last_active) VALUES (?, ?, ?, ?)',
                          (new_user_id, country_name, datetime.now(), datetime.now()))
        
        db_conn.commit()
        
        # اطلاع به مالک
        bot.reply_to(
            message,
            f"✅ بازیکن با آیدی {new_user_id} به کشور '{country_name}' اضافه شد!"
        )
        
        # اطلاع به بازیکن جدید
        try:
            bot.send_message(
                new_user_id,
                f"""🎉 **شما به بازی جنگ جهانی باستان اضافه شدید!**

🏛️ کشور شما: {country_name}
🎁 منبع ویژه: {get_special_resource(country_name)}

برای شروع بازی /start را بزنید.

💡 نکته: می‌توانید ارتش خود را تقویت کنید، معادن را توسعه دهید و با دیگر کشورها دیپلماسی کنید."""
            )
        except:
            bot.reply_to(message, f"⚠️ نتوانستم به کاربر {new_user_id} پیام بدم.")
            
    except ValueError:
        bot.reply_to(message, "⚠️ لطفاً یک آیدی عددی معتبر وارد کنید!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

def get_special_resource(country_name):
    cursor = db_conn.cursor()
    cursor.execute('SELECT special_resource FROM countries WHERE name = ?', (country_name,))
    result = cursor.fetchone()
    return result[0] if result else "نامشخص"

# ========== Webhook برای Render ==========
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
    return 'Ancient War Bot v2.0 is running!'

@app.route('/setwebhook')
def set_webhook():
    webhook_url = f"https://{request.host}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f'Webhook set to {webhook_url}'

# اجرای برنامه
if __name__ == '__main__':
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
        logger.info("✅ همه بخش‌ها فعال:")
        logger.info("   ⚔️ ارتش کامل با ۵ نوع سرباز")
        logger.info("   🛡️ سیستم دفاع کامل")
        logger.info("   🤝 دیپلماسی فعال")
        logger.info("   ⛏️ معادن و مزارع")
        logger.info("   📊 تولید روزانه منابع")
        
        bot.remove_webhook()
        bot.polling(none_stop=True)
