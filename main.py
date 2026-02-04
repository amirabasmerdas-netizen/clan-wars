import logging
import sqlite3
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات
BOT_TOKEN = "YOUR_BOT_TOKEN"  # اینجا را تغییر دهید
OWNER_ID = 8588773170

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
            last_active TIMESTAMP
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
    
    # جدول معادن
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            mine_type TEXT,
            level INTEGER DEFAULT 1,
            production_rate INTEGER DEFAULT 10,
            last_collected TIMESTAMP,
            x_position INTEGER,
            y_position INTEGER,
            FOREIGN KEY (player_id) REFERENCES players(user_id)
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
            attacker_losses INTEGER,
            defender_losses INTEGER,
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
            relation_type TEXT,
            status TEXT DEFAULT 'pending',
            message TEXT,
            created_at TIMESTAMP,
            expires_at TIMESTAMP
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

# ========== توابع کمکی ==========
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

def calculate_daily_production(player_id):
    """محاسبه تولید روزانه"""
    cursor = db_conn.cursor()
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (player_id,))
    player = cursor.fetchone()
    
    if not player:
        return None
    
    # تولید بر اساس سطح معادن
    columns = [desc[0] for desc in cursor.description]
    player_dict = dict(zip(columns, player))
    
    production = {
        'gold': player_dict['mine_gold_level'] * 50,
        'iron': player_dict['mine_iron_level'] * 30,
        'stone': player_dict['mine_stone_level'] * 40,
        'food': player_dict['farm_level'] * 100,
        'wood': 20  # تولید پایه چوب
    }
    
    # اعمال بونس کشور
    cursor.execute('SELECT special_resource FROM countries WHERE player_id = ?', (player_id,))
    country = cursor.fetchone()
    if country:
        resource = country[0]
        if resource == 'طلا':
            production['gold'] = int(production['gold'] * 1.5)
        elif resource == 'آهن':
            production['iron'] = int(production['iron'] * 1.5)
        elif resource == 'غذا':
            production['food'] = int(production['food'] * 1.5)
        elif resource == 'سنگ':
            production['stone'] = int(production['stone'] * 1.5)
    
    return production

# ========== منوها ==========
def main_menu(user_id):
    keyboard = []
    
    if user_id == OWNER_ID:
        keyboard = [
            [InlineKeyboardButton("👑 افزودن بازیکن", callback_data="add_player")],
            [InlineKeyboardButton("🌍 مشاهده کشورها", callback_data="view_countries")],
            [InlineKeyboardButton("📊 وضعیت منابع", callback_data="view_resources")],
            [InlineKeyboardButton("⚔️ ارتش و جنگ", callback_data="army_management")],
            [InlineKeyboardButton("🤝 دیپلماسی", callback_data="diplomacy")],
            [InlineKeyboardButton("⛏️ معادن و مزرعه", callback_data="mines_farms")],
            [InlineKeyboardButton("🔄 ریست بازی", callback_data="reset_game")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🏛️ مشاهده کشور من", callback_data="my_country")],
            [InlineKeyboardButton("📊 وضعیت منابع", callback_data="view_resources")],
            [InlineKeyboardButton("⚔️ ارتش و جنگ", callback_data="army_management")],
            [InlineKeyboardButton("🤝 دیپلماسی", callback_data="diplomacy")],
            [InlineKeyboardButton("⛏️ معادن و مزرعه", callback_data="mines_farms")],
            [InlineKeyboardButton("🌍 مشاهده کشورها", callback_data="view_countries")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def army_menu():
    keyboard = [
        [InlineKeyboardButton("👮 پیاده نظام", callback_data="army_infantry")],
        [InlineKeyboardButton("🏹 کمانداران", callback_data="army_archer")],
        [InlineKeyboardButton("🐎 سوارهنظام", callback_data="army_cavalry")],
        [InlineKeyboardButton("🗡️ نیزه‌داران", callback_data="army_spearman")],
        [InlineKeyboardButton("👤 دزدان", callback_data="army_thief")],
        [InlineKeyboardButton("⚔️ حمله به کشور", callback_data="attack_country")],
        [InlineKeyboardButton("🏰 دفاع از مرز", callback_data="defend_borders")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def defense_menu():
    keyboard = [
        [InlineKeyboardButton("🧱 دیوار", callback_data="defense_wall")],
        [InlineKeyboardButton("🏹 برج نگهبانی", callback_data="defense_tower")],
        [InlineKeyboardButton("🚪 دروازه", callback_data="defense_gate")],
        [InlineKeyboardButton("🛡️ تقویت کلی دفاع", callback_data="upgrade_all_defense")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="army_management")]
    ]
    return InlineKeyboardMarkup(keyboard)

def diplomacy_menu():
    keyboard = [
        [InlineKeyboardButton("🕊️ درخواست صلح", callback_data="peace_request")],
        [InlineKeyboardButton("⚔️ اعلام جنگ", callback_data="declare_war")],
        [InlineKeyboardButton("🤝 درخواست اتحاد", callback_data="request_alliance")],
        [InlineKeyboardButton("💰 پیشنهاد تجارت", callback_data="trade_offer")],
        [InlineKeyboardButton("📜 مشاهده پیشنهادها", callback_data="view_diplomacy_offers")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def mines_menu():
    keyboard = [
        [InlineKeyboardButton("💰 معدن طلا", callback_data="mine_gold")],
        [InlineKeyboardButton("⚒️ معدن آهن", callback_data="mine_iron")],
        [InlineKeyboardButton("🪨 معدن سنگ", callback_data="mine_stone")],
        [InlineKeyboardButton("🌾 مزرعه غذا", callback_data="farm_food")],
        [InlineKeyboardButton("🏗️ کارخانه سرباز", callback_data="barracks")],
        [InlineKeyboardButton("📦 جمع‌آوری منابع", callback_data="collect_resources")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    user = update.effective_user
    user_id = user.id
    
    # ثبت کاربر در دیتابیس
    cursor = db_conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO players (user_id, username, join_date, last_active) VALUES (?, ?, ?, ?)',
                  (user_id, user.username or user.first_name, datetime.now(), datetime.now()))
    db_conn.commit()
    
    welcome_text = f"""👋 سلام {user.first_name}!
به بازی جنگ جهانی باستان خوش آمدید.

🎮 شما: {'👑 مالک بازی' if user_id == OWNER_ID else '🎮 بازیکن'}

🏛️ مدیریت کشور باستانی خود
⚔️ ارتش‌های متنوع بسازید
🤝 با دیگران دیپلماسی کنید
⛏️ معادن را توسعه دهید

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"""
    
    await update.message.reply_text(welcome_text, reply_markup=main_menu(user_id))

# ========== هندلر اصلی دکمه‌ها ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cursor = db_conn.cursor()
    
    if query.data == "main_menu":
        await query.edit_message_text(
            f"منوی اصلی\nشما: {'👑 مالک' if user_id == OWNER_ID else '🎮 بازیکن'}",
            reply_markup=main_menu(user_id)
        )
    
    # ========== بخش ارتش و جنگ ==========
    elif query.data == "army_management":
        cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
        player = cursor.fetchone()
        
        if player:
            columns = [desc[0] for desc in cursor.description]
            player_data = dict(zip(columns, player))
            
            army_power = calculate_army_power(player_data)
            defense_power = calculate_defense_power(player_data)
            
            text = f"""⚔️ **مدیریت ارتش و جنگ**

👮 **نیروهای شما:**
• پیاده نظام: {player_data['army_infantry']}
• کمانداران: {player_data['army_archer']}
• سوارهنظام: {player_data['army_cavalry']}
• نیزه‌داران: {player_data['army_spearman']}
• دزدان: {player_data['army_thief']}

🛡️ **سازه‌های دفاعی:**
• دیوار: {player_data['defense_wall']}
• برج نگهبانی: {player_data['defense_tower']}
• دروازه: {player_data['defense_gate']}

⚡ **قدرت کلی:**
• قدرت حمله: {army_power:.1f}
• قدرت دفاع: {defense_power:.1f}"""
        else:
            text = "⚠️ شما هنوز کشوری ندارید!"
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=army_menu()
        )
    
    # ========== انواع سربازان ==========
    elif query.data in ["army_infantry", "army_archer", "army_cavalry", "army_spearman", "army_thief"]:
        army_types = {
            "army_infantry": {"name": "پیاده نظام", "cost_gold": 10, "cost_food": 20, "column": "army_infantry"},
            "army_archer": {"name": "کمانداران", "cost_gold": 15, "cost_food": 10, "column": "army_archer"},
            "army_cavalry": {"name": "سوارهنظام", "cost_gold": 30, "cost_food": 40, "column": "army_cavalry"},
            "army_spearman": {"name": "نیزه‌داران", "cost_gold": 12, "cost_food": 15, "column": "army_spearman"},
            "army_thief": {"name": "دزدان", "cost_gold": 5, "cost_food": 5, "column": "army_thief"}
        }
        
        army_info = army_types[query.data]
        cursor.execute('SELECT gold, food FROM players WHERE user_id = ?', (user_id,))
        player = cursor.fetchone()
        
        if player:
            gold, food = player
            text = f"""👮 **{army_info['name']}**

💰 هزینه استخدام 10 نفر:
• طلا: {army_info['cost_gold'] * 10}
• غذا: {army_info['cost_food'] * 10}

💎 منابع شما:
• طلا: {gold}
• غذا: {food}

تعداد مورد نظر برای استخدام را وارد کنید (هر 10 نفر):"""
            
            await query.edit_message_text(
                text=text,
                parse_mode='Markdown'
            )
            
            # ذخیره اطلاعات برای مرحله بعد
            context.user_data['recruit_type'] = query.data
            context.user_data['recruit_info'] = army_info
            
    # ========== حمله به کشور ==========
    elif query.data == "attack_country":
        cursor.execute('''
            SELECT c.name, c.special_resource, 
                   COALESCE(p.username, 'بدون بازیکن') as player_name
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
            WHERE c.controller = 'HUMAN' AND c.player_id != ?
        ''', (user_id,))
        
        countries = cursor.fetchall()
        
        if countries:
            keyboard = []
            for name, resource, player in countries:
                keyboard.append([InlineKeyboardButton(
                    f"⚔️ حمله به {name} ({player})",
                    callback_data=f"attack_{name}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="army_management")])
            
            text = "⚔️ **حمله به کشورهای دیگر**\n\nکشورهای قابل حمله:"
        else:
            text = "⚠️ هیچ کشور انسانی دیگری برای حمله وجود ندارد!"
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="army_management")]]
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ========== دفاع از مرز ==========
    elif query.data == "defend_borders":
        cursor.execute('''
            SELECT defense_wall, defense_tower, defense_gate, 
                   gold, stone, iron
            FROM players WHERE user_id = ?
        ''', (user_id,))
        
        player = cursor.fetchone()
        
        if player:
            defense_wall, defense_tower, defense_gate, gold, stone, iron = player
            
            text = f"""🏰 **دفاع از مرزها**

🛡️ **وضعیت فعلی دفاع:**
• دیوار: {defense_wall}
• برج نگهبانی: {defense_tower}
• دروازه: {defense_gate}

💰 **منابع شما:**
• طلا: {gold}
• سنگ: {stone}
• آهن: {iron}

🛠️ **هزینه تقویت هر واحد:**
• دیوار: 20 سنگ + 10 طلا
• برج: 30 سنگ + 20 آهن + 15 طلا
• دروازه: 25 سنگ + 15 آهن + 10 طلا"""

            await query.edit_message_text(
                text=text,
                parse_mode='Markdown',
                reply_markup=defense_menu()
            )
    
    # ========== تقویت دفاع ==========
    elif query.data in ["defense_wall", "defense_tower", "defense_gate"]:
        defense_types = {
            "defense_wall": {"name": "دیوار", "cost_stone": 20, "cost_gold": 10, "column": "defense_wall"},
            "defense_tower": {"name": "برج نگهبانی", "cost_stone": 30, "cost_iron": 20, "cost_gold": 15, "column": "defense_tower"},
            "defense_gate": {"name": "دروازه", "cost_stone": 25, "cost_iron": 15, "cost_gold": 10, "column": "defense_gate"}
        }
        
        defense_info = defense_types[query.data]
        cursor.execute('SELECT gold, stone, iron FROM players WHERE user_id = ?', (user_id,))
        player = cursor.fetchone()
        
        if player:
            gold, stone, iron = player
            costs = []
            if 'cost_gold' in defense_info:
                costs.append(f"💰 طلا: {defense_info['cost_gold']}")
            if 'cost_stone' in defense_info:
                costs.append(f"🪨 سنگ: {defense_info['cost_stone']}")
            if 'cost_iron' in defense_info:
                costs.append(f"⚒️ آهن: {defense_info['cost_iron']}")
            
            text = f"""🛡️ **تقویت {defense_info['name']}**

📋 هزینه تقویت هر واحد:
{chr(10).join(costs)}

💎 منابع شما:
• طلا: {gold}
• سنگ: {stone}
• آهن: {iron}

تعداد واحد مورد نظر برای تقویت را وارد کنید:"""
            
            await query.edit_message_text(
                text=text,
                parse_mode='Markdown'
            )
            
            context.user_data['defense_type'] = query.data
            context.user_data['defense_info'] = defense_info
    
    # ========== دیپلماسی ==========
    elif query.data == "diplomacy":
        cursor.execute('''
            SELECT c.name, c.special_resource, p.username
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
            WHERE c.controller = 'HUMAN' AND c.player_id != ?
        ''', (user_id,))
        
        countries = cursor.fetchall()
        
        text = "🤝 **دیپلماسی**\n\n"
        if countries:
            text += "🏛️ **کشورهای انسانی دیگر:**\n"
            for name, resource, player in countries:
                text += f"• {name} ({player}) - منبع: {resource}\n"
            text += "\nبرای ارتباط با کشورها گزینه مورد نظر را انتخاب کنید:"
        else:
            text += "⚠️ هیچ کشور انسانی دیگری برای ارتباط وجود ندارد!"
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=diplomacy_menu()
        )
    
    # ========== اقدامات دیپلماتیک ==========
    elif query.data in ["peace_request", "declare_war", "request_alliance", "trade_offer"]:
        actions = {
            "peace_request": {"name": "درخواست صلح", "emoji": "🕊️"},
            "declare_war": {"name": "اعلام جنگ", "emoji": "⚔️"},
            "request_alliance": {"name": "درخواست اتحاد", "emoji": "🤝"},
            "trade_offer": {"name": "پیشنهاد تجارت", "emoji": "💰"}
        }
        
        action_info = actions[query.data]
        cursor.execute('''
            SELECT c.name, p.username
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
            WHERE c.controller = 'HUMAN' AND c.player_id != ?
        ''', (user_id,))
        
        countries = cursor.fetchall()
        
        if countries:
            keyboard = []
            for name, target_player in countries:
                keyboard.append([InlineKeyboardButton(
                    f"{action_info['emoji']} به {name} ({target_player})",
                    callback_data=f"diplomacy_{query.data}_{name}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="diplomacy")])
            
            text = f"{action_info['emoji']} **{action_info['name']}**\n\nکشور مورد نظر را انتخاب کنید:"
        else:
            text = "⚠️ هیچ کشور انسانی دیگری برای ارتباط وجود ندارد!"
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="diplomacy")]]
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ========== معادن و مزرعه ==========
    elif query.data == "mines_farms":
        cursor.execute('''
            SELECT mine_gold_level, mine_iron_level, mine_stone_level, 
                   farm_level, barracks_level,
                   gold, iron, stone, food, wood
            FROM players WHERE user_id = ?
        ''', (user_id,))
        
        player = cursor.fetchone()
        
        if player:
            mine_gold, mine_iron, mine_stone, farm, barracks, gold, iron, stone, food, wood = player
            
            # محاسبه تولید
            production = calculate_daily_production(user_id)
            
            text = f"""⛏️ **معادن و مزارع**

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
• چوب: {wood}"""
        else:
            text = "⚠️ شما هنوز کشوری ندارید!"
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=mines_menu()
        )
    
    # ========== انواع معادن ==========
    elif query.data in ["mine_gold", "mine_iron", "mine_stone", "farm_food", "barracks"]:
        mine_types = {
            "mine_gold": {"name": "معدن طلا", "resource": "gold", "column": "mine_gold_level", 
                          "cost_stone": 100, "cost_wood": 50, "base_production": 50},
            "mine_iron": {"name": "معدن آهن", "resource": "iron", "column": "mine_iron_level", 
                          "cost_stone": 80, "cost_wood": 60, "base_production": 30},
            "mine_stone": {"name": "معدن سنگ", "resource": "stone", "column": "mine_stone_level", 
                           "cost_stone": 50, "cost_wood": 70, "base_production": 40},
            "farm_food": {"name": "مزرعه غذا", "resource": "food", "column": "farm_level", 
                          "cost_wood": 100, "cost_gold": 30, "base_production": 100},
            "barracks": {"name": "کارخانه سرباز", "resource": "training", "column": "barracks_level", 
                         "cost_stone": 200, "cost_wood": 150, "cost_gold": 100}
        }
        
        mine_info = mine_types[query.data]
        cursor.execute('SELECT stone, wood, gold FROM players WHERE user_id = ?', (user_id,))
        player = cursor.fetchone()
        
        if player:
            stone, wood, gold = player
            costs = []
            if 'cost_stone' in mine_info:
                costs.append(f"🪨 سنگ: {mine_info['cost_stone']}")
            if 'cost_wood' in mine_info:
                costs.append(f"🌲 چوب: {mine_info['cost_wood']}")
            if 'cost_gold' in mine_info:
                costs.append(f"💰 طلا: {mine_info['cost_gold']}")
            
            # گرفتن سطح فعلی
            cursor.execute(f'SELECT {mine_info["column"]} FROM players WHERE user_id = ?', (user_id,))
            current_level = cursor.fetchone()[0]
            
            production = mine_info.get('base_production', 0) * current_level if 'base_production' in mine_info else 0
            
            text = f"""🏭 **{mine_info['name']}**

📊 **وضعیت فعلی:**
• سطح: {current_level}
• تولید: {production} در روز

🛠️ **هزینه ارتقاء به سطح {current_level + 1}:**
{chr(10).join(costs)}

💎 **منابع شما:**
• سنگ: {stone}
• چوب: {wood}
• طلا: {gold}

آیا می‌خواهید این سازه را ارتقاء دهید؟"""

            keyboard = [
                [
                    InlineKeyboardButton("✅ بله، ارتقاء بده", callback_data=f"upgrade_{query.data}"),
                    InlineKeyboardButton("❌ خیر", callback_data="mines_farms")
                ]
            ]
            
            await query.edit_message_text(
                text=text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    # ========== ارتقاء معدن ==========
    elif query.data.startswith("upgrade_"):
        mine_type = query.data.replace("upgrade_", "")
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
                    # کسر منابع
                    set_clause = []
                    values = []
                    
                    if 'cost_stone' in mine_info:
                        set_clause.append("stone = stone - ?")
                        values.append(mine_info['cost_stone'])
                    if 'cost_wood' in mine_info:
                        set_clause.append("wood = wood - ?")
                        values.append(mine_info['cost_wood'])
                    if 'cost_gold' in mine_info:
                        set_clause.append("gold = gold - ?")
                        values.append(mine_info['cost_gold'])
                    
                    # افزایش سطح
                    set_clause.append(f"{mine_info['column']} = {mine_info['column']} + 1")
                    
                    # اجرای آپدیت
                    update_query = f"UPDATE players SET {', '.join(set_clause)} WHERE user_id = ?"
                    values.append(user_id)
                    cursor.execute(update_query, values)
                    db_conn.commit()
                    
                    text = f"✅ سازه با موفقیت ارتقاء یافت!"
                else:
                    text = f"❌ منابع کافی نیست!\n\nمنابع недостаافی:\n{chr(10).join(missing_resources)}"
                
                await query.edit_message_text(
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=mines_menu()
                )
    
    # ========== جمع‌آوری منابع ==========
    elif query.data == "collect_resources":
        production = calculate_daily_production(user_id)
        
        if production:
            # افزودن منابع به بازیکن
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
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=mines_menu()
        )
    
    # ========== بقیه هندلرها (مشابه قبل) ==========
    elif query.data == "view_resources":
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
• چوب: {production['wood'] if production else 0}"""
        else:
            text = "⚠️ شما هنوز ثبت‌نام نکرده‌اید."
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    # ========== حمله به کشور خاص ==========
    elif query.data.startswith("attack_"):
        target_country = query.data.replace("attack_", "")
        
        # گرفتن اطلاعات مهاجم
        cursor.execute('''
            SELECT p.army_infantry, p.army_archer, p.army_cavalry, 
                   p.army_spearman, p.army_thief, c.name
            FROM players p
            LEFT JOIN countries c ON p.country = c.name
            WHERE p.user_id = ?
        ''', (user_id,))
        
        attacker = cursor.fetchone()
        
        if not attacker or not attacker[5]:  # اگر مهاجم کشوری ندارد
            await query.edit_message_text(
                text="⚠️ شما کشوری ندارید که بتوانید حمله کنید!",
                reply_markup=main_menu(user_id)
            )
            return
        
        attacker_army = attacker[:5]
        attacker_country = attacker[5]
        
        # گرفتن اطلاعات مدافع
        cursor.execute('''
            SELECT p.user_id, p.army_infantry, p.army_archer, p.army_cavalry,
                   p.army_spearman, p.army_thief, p.defense_wall, p.defense_tower, p.defense_gate
            FROM players p
            LEFT JOIN countries c ON p.country = c.name
            WHERE c.name = ?
        ''', (target_country,))
        
        defender = cursor.fetchone()
        
        if not defender:
            await query.edit_message_text(
                text=f"⚠️ کشور {target_country} یافت نشد!",
                reply_markup=main_menu(user_id)
            )
            return
        
        defender_id, defender_army, defender_defense = defender[0], defender[1:6], defender[6:9]
        
        # شبیه‌سازی نبرد
        battle_result = simulate_battle(attacker_army, defender_army, defender_defense)
        
        # ثبت نبرد در دیتابیس
        cursor.execute('''
            INSERT INTO battles (attacker_id, defender_id, attacker_country, defender_country, 
                               result, attacker_losses, defender_losses, gold_looted, 
                               iron_looted, food_looted, battle_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, defender_id, attacker_country, target_country,
            battle_result['result'],
            battle_result['attacker_losses'],
            battle_result['defender_losses'],
            battle_result['gold_looted'],
            battle_result['iron_looted'],
            battle_result['food_looted'],
            datetime.now()
        ))
        
        # آپدیت نیروهای بازمانده
        # آپدیت مهاجم
        cursor.execute('''
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
        
        # آپدیت مدافع
        cursor.execute('''
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
            battle_result['gold_looted'],
            battle_result['iron_looted'],
            battle_result['food_looted'],
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
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
    
    # ========== دیپلماسی به کشور خاص ==========
    elif query.data.startswith("diplomacy_"):
        parts = query.data.split("_")
        if len(parts) >= 3:
            action = parts[1]
            target_country = "_".join(parts[2:])
            
            actions_info = {
                "peace": {"name": "درخواست صلح", "cost": 100},
                "war": {"name": "اعلام جنگ", "cost": 0},
                "alliance": {"name": "درخواست اتحاد", "cost": 200},
                "trade": {"name": "پیشنهاد تجارت", "cost": 50}
            }
            
            if action in actions_info:
                action_info = actions_info[action]
                
                # پیدا کردن ID مدافع
                cursor.execute('SELECT player_id FROM countries WHERE name = ?', (target_country,))
                target_result = cursor.fetchone()
                
                if target_result and target_result[0]:
                    target_player_id = target_result[0]
                    
                    # ثبت درخواست دیپلماسی
                    cursor.execute('''
                        INSERT INTO diplomacy (from_player_id, to_player_id, relation_type, 
                                             message, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        target_player_id,
                        action,
                        f"{action_info['name']} از طرف {user_id}",
                        datetime.now(),
                        datetime.now()
                    ))
                    db_conn.commit()
                    
                    text = f"""✅ **{action_info['name']} ارسال شد!**

🏛️ به کشور: {target_country}
📋 نوع: {action_info['name']}
⏰ وضعیت: در انتظار پاسخ

پیام شما برای بازیکن هدف ارسال شد."""
                else:
                    text = f"⚠️ کشور {target_country} بازیکن ندارد!"
                
                await query.edit_message_text(
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=main_menu(user_id)
                )
    
    # ========== مشاهده پیشنهادهای دیپلماسی ==========
    elif query.data == "view_diplomacy_offers":
        cursor.execute('''
            SELECT d.id, d.relation_type, d.message, d.created_at,
                   c.name as from_country, p.username as from_player
            FROM diplomacy d
            LEFT JOIN countries c ON d.from_player_id = c.player_id
            LEFT JOIN players p ON d.from_player_id = p.user_id
            WHERE d.to_player_id = ? AND d.status = 'pending'
            ORDER BY d.created_at DESC
        ''', (user_id,))
        
        offers = cursor.fetchall()
        
        if offers:
            text = "📜 **پیشنهادهای دیپلماسی دریافتی:**\n\n"
            for i, offer in enumerate(offers, 1):
                offer_id, relation_type, message, created_at, from_country, from_player = offer
                
                relation_names = {
                    "peace": "🕊️ درخواست صلح",
                    "war": "⚔️ اعلام جنگ",
                    "alliance": "🤝 درخواست اتحاد",
                    "trade": "💰 پیشنهاد تجارت"
                }
                
                text += f"{i}. {relation_names.get(relation_type, relation_type)}\n"
                text += f"   از: {from_country} ({from_player})\n"
                text += f"   تاریخ: {created_at}\n"
                text += f"   [ID: {offer_id}]\n"
                text += f"   {'─'*30}\n"
            
            text += "\nبرای پاسخ به هر پیشنهاد، شماره آن را وارد کنید:"
            
            await query.edit_message_text(
                text=text,
                parse_mode='Markdown'
            )
            
            context.user_data['awaiting_diplomacy_response'] = True
            context.user_data['pending_offers'] = offers
        else:
            text = "📭 **هیچ پیشنهاد دیپلماسی جدیدی ندارید.**"
            
            await query.edit_message_text(
                text=text,
                parse_mode='Markdown',
                reply_markup=diplomacy_menu()
            )

# ========== تابع شبیه‌سازی نبرد ==========
def simulate_battle(attacker_army, defender_army, defender_defense):
    """شبیه‌سازی نبرد با جزئیات کامل"""
    
    # محاسبه قدرت حمله
    attacker_power = (
        attacker_army[0] * 1.0 +    # پیاده نظام
        attacker_army[1] * 1.5 +    # کماندار
        attacker_army[2] * 2.0 +    # سواره نظام
        attacker_army[3] * 1.2 +    # نیزه‌دار
        attacker_army[4] * 0.8      # دزد
    )
    
    # محاسبه قدرت دفاع
    defender_power = (
        defender_army[0] * 1.0 +    # پیاده نظام
        defender_army[1] * 1.5 +    # کماندار
        defender_army[2] * 2.0 +    # سواره نظام
        defender_army[3] * 1.2 +    # نیزه‌دار
        defender_army[4] * 0.8 +    # دزد
        defender_defense[0] * 0.5 + # دیوار
        defender_defense[1] * 1.0 + # برج
        defender_defense[2] * 0.8   # دروازه
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
        
        # تلفات مهاجم (کم)
        result['attacker_infantry_loss'] = int(attacker_army[0] * (1 - victory_ratio) * 0.2)
        result['attacker_archer_loss'] = int(attacker_army[1] * (1 - victory_ratio) * 0.15)
        result['attacker_cavalry_loss'] = int(attacker_army[2] * (1 - victory_ratio) * 0.1)
        result['attacker_spearman_loss'] = int(attacker_army[3] * (1 - victory_ratio) * 0.18)
        result['attacker_thief_loss'] = int(attacker_army[4] * (1 - victory_ratio) * 0.25)
        
        # تلفات مدافع (زیاد)
        result['defender_infantry_loss'] = int(defender_army[0] * victory_ratio * 0.7)
        result['defender_archer_loss'] = int(defender_army[1] * victory_ratio * 0.6)
        result['defender_cavalry_loss'] = int(defender_army[2] * victory_ratio * 0.5)
        result['defender_spearman_loss'] = int(defender_army[3] * victory_ratio * 0.65)
        result['defender_thief_loss'] = int(defender_army[4] * victory_ratio * 0.8)
        
        # آسیب به سازه‌های دفاعی
        result['defense_wall_damage'] = int(defender_defense[0] * victory_ratio * 0.4)
        result['defense_tower_damage'] = int(defender_defense[1] * victory_ratio * 0.3)
        result['defense_gate_damage'] = int(defender_defense[2] * victory_ratio * 0.5)
        
        # غنائم
        result['gold_looted'] = random.randint(100, 500)
        result['iron_looted'] = random.randint(50, 200)
        result['food_looted'] = random.randint(200, 800)
        
    else:
        # دفاع موفق
        defense_ratio = (defender_power - attacker_power) / defender_power
        result['result'] = "شکست"
        
        # تلفات مهاجم (زیاد)
        result['attacker_infantry_loss'] = int(attacker_army[0] * defense_ratio * 0.6)
        result['attacker_archer_loss'] = int(attacker_army[1] * defense_ratio * 0.5)
        result['attacker_cavalry_loss'] = int(attacker_army[2] * defense_ratio * 0.4)
        result['attacker_spearman_loss'] = int(attacker_army[3] * defense_ratio * 0.55)
        result['attacker_thief_loss'] = int(attacker_army[4] * defense_ratio * 0.7)
        
        # تلفات مدافع (کم)
        result['defender_infantry_loss'] = int(defender_army[0] * (1 - defense_ratio) * 0.15)
        result['defender_archer_loss'] = int(defender_army[1] * (1 - defense_ratio) * 0.1)
        result['defender_cavalry_loss'] = int(defender_army[2] * (1 - defense_ratio) * 0.05)
        result['defender_spearman_loss'] = int(defender_army[3] * (1 - defense_ratio) * 0.12)
        result['defender_thief_loss'] = int(defender_army[4] * (1 - defense_ratio) * 0.2)
        
        # آسیب کم به سازه‌های دفاعی
        result['defense_wall_damage'] = int(defender_defense[0] * (1 - defense_ratio) * 0.1)
        result['defense_tower_damage'] = int(defender_defense[1] * (1 - defense_ratio) * 0.05)
        result['defense_gate_damage'] = int(defender_defense[2] * (1 - defense_ratio) * 0.15)
        
        # غنائم کم
        result['gold_looted'] = random.randint(10, 50)
        result['iron_looted'] = random.randint(5, 20)
        result['food_looted'] = random.randint(20, 80)
    
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

# ========== هندلر پیام‌های متنی ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    user_id = update.effective_user.id
    text = update.message.text
    cursor = db_conn.cursor()
    
    # استخدام سرباز
    if 'recruit_type' in context.user_data:
        try:
            amount = int(text)
            if amount <= 0:
                await update.message.reply_text("⚠️ تعداد باید بیشتر از 0 باشد!")
                return
            
            recruit_info = context.user_data['recruit_info']
            unit_count = amount * 10  # هر واحد = 10 سرباز
            
            # بررسی منابع
            cursor.execute('SELECT gold, food FROM players WHERE user_id = ?', (user_id,))
            resources = cursor.fetchone()
            
            if resources:
                gold, food = resources
                total_gold_cost = recruit_info['cost_gold'] * unit_count
                total_food_cost = recruit_info['cost_food'] * unit_count
                
                if gold >= total_gold_cost and food >= total_food_cost:
                    # کسر منابع و افزایش نیرو
                    cursor.execute(f'''
                        UPDATE players 
                        SET gold = gold - ?, 
                            food = food - ?,
                            {recruit_info['column']} = {recruit_info['column']} + ?
                        WHERE user_id = ?
                    ''', (total_gold_cost, total_food_cost, unit_count, user_id))
                    db_conn.commit()
                    
                    await update.message.reply_text(
                        f"""✅ استخدام موفق!

👮 {unit_count} نفر {recruit_info['name']} استخدام شدند.

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
                    
                    await update.message.reply_text(
                        f"❌ منابع کافی نیست!\n\nمنابع مورد نیاز:\n{chr(10).join(missing)}",
                        reply_markup=main_menu(user_id)
                    )
            
            # پاک کردن داده‌های موقت
            context.user_data.pop('recruit_type', None)
            context.user_data.pop('recruit_info', None)
            
        except ValueError:
            await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید!")
    
    # تقویت دفاع
    elif 'defense_type' in context.user_data:
        try:
            amount = int(text)
            if amount <= 0:
                await update.message.reply_text("⚠️ تعداد باید بیشتر از 0 باشد!")
                return
            
            defense_info = context.user_data['defense_info']
            
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
                    
                    await update.message.reply_text(
                        f"""✅ تقویت موفق!

🛡️ {amount} واحد {defense_info['name']} تقویت شد.

📋 هزینه‌ها:
{chr(10).join(cost_text)}

دفاع شما تقویت شد.""",
                        reply_markup=main_menu(user_id)
                    )
                else:
                    await update.message.reply_text(
                        f"❌ منابع کافی نیست!\n\nمنابع مورد نیاز:\n{chr(10).join(missing_resources)}",
                        reply_markup=main_menu(user_id)
                    )
            
            # پاک کردن داده‌های موقت
            context.user_data.pop('defense_type', None)
            context.user_data.pop('defense_info', None)
            
        except ValueError:
            await update.message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید!")
    
    # پاسخ به دیپلماسی
    elif context.user_data.get('awaiting_diplomacy_response'):
        try:
            offer_index = int(text) - 1
            offers = context.user_data.get('pending_offers', [])
            
            if 0 <= offer_index < len(offers):
                offer_id, relation_type, message, created_at, from_country, from_player = offers[offer_index]
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ پذیرش", callback_data=f"diplomacy_accept_{offer_id}"),
                        InlineKeyboardButton("❌ رد", callback_data=f"diplomacy_reject_{offer_id}")
                    ],
                    [InlineKeyboardButton("⏸️ تعلیق", callback_data=f"diplomacy_pending_{offer_id}")]
                ]
                
                relation_names = {
                    "peace": "🕊️ درخواست صلح",
                    "war": "⚔️ اعلام جنگ",
                    "alliance": "🤝 درخواست اتحاد",
                    "trade": "💰 پیشنهاد تجارت"
                }
                
                await update.message.reply_text(
                    f"""📋 **پیشنهاد #{offer_index + 1}**

🏛️ از کشور: {from_country}
👤 بازیکن: {from_player}
📝 نوع: {relation_names.get(relation_type, relation_type)}
📨 پیام: {message}
📅 تاریخ: {created_at}

پاسخ خود را انتخاب کنید:""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                # پاک کردن داده‌های موقت
                context.user_data.pop('awaiting_diplomacy_response', None)
                context.user_data.pop('pending_offers', None)
            else:
                await update.message.reply_text("⚠️ شماره پیشنهاد نامعتبر است!")
        
        except ValueError:
            await update.message.reply_text("⚠️ لطفاً شماره پیشنهاد را وارد کنید!")
    
    # افزودن بازیکن (مالک)
    elif user_id == OWNER_ID and 'selected_country' in context.user_data:
        try:
            new_user_id = int(text)
            country_name = context.user_data.pop('selected_country')
            
            # بررسی اینکه کشور آزاد است
            cursor.execute('SELECT controller FROM countries WHERE name = ?', (country_name,))
            country = cursor.fetchone()
            
            if not country or country[0] != "AI":
                await update.message.reply_text("❌ این کشور قبلاً اشغال شده است!")
                return
            
            # اختصاص کشور به بازیکن
            cursor.execute('UPDATE countries SET controller = "HUMAN", player_id = ? WHERE name = ?',
                          (new_user_id, country_name))
            
            # به‌روزرسانی بازیکن
            cursor.execute('UPDATE players SET country = ? WHERE user_id = ?', (country_name, new_user_id))
            
            # اگر بازیکن وجود ندارد، ایجاد کن
            if cursor.rowcount == 0:
                cursor.execute('INSERT INTO players (user_id, country, join_date) VALUES (?, ?, ?)',
                              (new_user_id, country_name, datetime.now()))
            
            db_conn.commit()
            
            # اطلاع به مالک
            await update.message.reply_text(
                f"✅ بازیکن با آیدی {new_user_id} به کشور '{country_name}' اضافه شد!"
            )
            
        except ValueError:
            await update.message.reply_text("⚠️ لطفاً یک آیدی عددی معتبر وارد کنید!")
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    else:
        await update.message.reply_text(
            "لطفاً از دکمه‌های منو استفاده کنید.\nبرای شروع مجدد: /start",
            reply_markup=main_menu(user_id)
        )

# ========== هندلر پاسخ دیپلماسی ==========
async def diplomacy_response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به درخواست‌های دیپلماسی"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("diplomacy_"):
        parts = data.split("_")
        if len(parts) >= 3:
            action = parts[1]
            offer_id = parts[2]
            
            cursor = db_conn.cursor()
            
            # گرفتن اطلاعات پیشنهاد
            cursor.execute('''
                SELECT d.relation_type, d.from_player_id, d.message,
                       c.name as from_country, p.username as from_player
                FROM diplomacy d
                LEFT JOIN countries c ON d.from_player_id = c.player_id
                LEFT JOIN players p ON d.from_player_id = p.user_id
                WHERE d.id = ? AND d.to_player_id = ?
            ''', (offer_id, user_id))
            
            offer = cursor.fetchone()
            
            if offer:
                relation_type, from_player_id, message, from_country, from_player = offer
                
                relation_names = {
                    "peace": "صلح",
                    "war": "جنگ",
                    "alliance": "اتحاد",
                    "trade": "تجارت"
                }
                
                action_texts = {
                    "accept": "✅ پذیرفته شد",
                    "reject": "❌ رد شد",
                    "pending": "⏸️ تعلیق شد"
                }
                
                # آپدیت وضعیت
                cursor.execute('UPDATE diplomacy SET status = ? WHERE id = ?', (action, offer_id))
                db_conn.commit()
                
                # اطلاع به فرستنده
                try:
                    # اینجا می‌توانید به فرستنده هم اطلاع دهید
                    pass
                except:
                    pass
                
                await query.edit_message_text(
                    f"""📨 **پاسخ دیپلماسی**

{action_texts.get(action, action)}

📋 پیشنهاد: {relation_names.get(relation_type, relation_type)}
🏛️ از کشور: {from_country}
👤 بازیکن: {from_player}
📝 پیام: {message}

پاسخ شما ثبت شد.""",
                    reply_markup=main_menu(user_id)
                )
            else:
                await query.edit_message_text(
                    "⚠️ پیشنهاد یافت نشد!",
                    reply_markup=main_menu(user_id)
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
    application.add_handler(CallbackQueryHandler(diplomacy_response_handler, pattern="^diplomacy_(accept|reject|pending)_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # اجرای ربات
    print("🤖 ربات در حال راه‌اندازی...")
    print(f"🔑 مالک: {OWNER_ID}")
    print("🔄 در حالت Polling...")
    print("✅ همه بخش‌ها فعال شدند:")
    print("   ⚔️ ارتش کامل با ۵ نوع سرباز")
    print("   🛡️ سیستم دفاع کامل")
    print("   🤝 دیپلماسی فعال")
    print("   ⛏️ معادن و مزارع")
    print("   📊 تولید روزانه منابع")
    
    application.run_polling()

if __name__ == '__main__':
    main()
