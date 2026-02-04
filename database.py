import sqlite3
import logging
import random
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.config = Config()
        self.conn = sqlite3.connect('aryaboom.db', check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row  # بازگرداندن دیکشنری
        self.init_db()
    
    def init_db(self):
        """ایجاد جداول دیتابیس"""
        cursor = self.conn.cursor()
        
        # جدول کاربران (هر کاربر = یک قبیله)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                clan_name TEXT NOT NULL,
                clan_index INTEGER NOT NULL,
                level INTEGER DEFAULT 1,
                power INTEGER DEFAULT 100,
                gold INTEGER DEFAULT 1000,
                food INTEGER DEFAULT 500,
                wood INTEGER DEFAULT 300,
                stone INTEGER DEFAULT 200,
                troops INTEGER DEFAULT 50,
                territories INTEGER DEFAULT 1,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                kills INTEGER DEFAULT 0,
                total_income INTEGER DEFAULT 0,
                total_expense INTEGER DEFAULT 0,
                invite_code TEXT UNIQUE,
                registered_by INTEGER,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(clan_index)  -- هر قبیله فقط یک کاربر می‌تواند داشته باشد
            )
        ''')
        
        # جدول اتحادها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alliances (
                alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                creator_id INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                member_count INTEGER DEFAULT 1
            )
        ''')
        
        # جدول اعضای اتحاد
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alliance_members (
                alliance_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (alliance_id, user_id),
                FOREIGN KEY (alliance_id) REFERENCES alliances(alliance_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # جدول AI قبایل (برای قبایل بدون کاربر)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_clans (
                clan_name TEXT PRIMARY KEY,
                clan_index INTEGER UNIQUE,
                ai_type TEXT DEFAULT 'defensive',
                aggression_level REAL DEFAULT 0.5,
                power_level INTEGER DEFAULT 100,
                gold INTEGER DEFAULT 1000,
                food INTEGER DEFAULT 500,
                wood INTEGER DEFAULT 300,
                stone INTEGER DEFAULT 200,
                troops INTEGER DEFAULT 50,
                territories TEXT DEFAULT '[]',
                last_action TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول جنگ‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS battles (
                battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_id INTEGER,
                defender_id INTEGER,
                attacker_clan TEXT,
                defender_clan TEXT,
                result TEXT,
                attacker_losses INTEGER,
                defender_losses INTEGER,
                gold_loot INTEGER,
                food_loot INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                FOREIGN KEY (attacker_id) REFERENCES users(user_id),
                FOREIGN KEY (defender_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول ساختمان‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buildings (
                building_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                building_type TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                position_x INTEGER,
                position_y INTEGER,
                built_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                upgrade_finish TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()
        logger.info("✅ Database initialized successfully")
        
        # ایجاد AI برای قبایل خالی
        self.create_ai_for_empty_clans()
    
    def create_ai_for_empty_clans(self):
        """ایجاد AI برای قبایلی که کاربر ندارند"""
        cursor = self.conn.cursor()
        
        # دریافت قبایل دارای کاربر
        cursor.execute("SELECT DISTINCT clan_index FROM users WHERE is_active = 1")
        occupied_clans = [row[0] for row in cursor.fetchall()]
        
        # ایجاد AI برای قبایل خالی
        for i, clan in enumerate(self.config.CLANS):
            if i not in occupied_clans:
                cursor.execute('''
                    INSERT OR IGNORE INTO ai_clans (
                        clan_name, clan_index, ai_type, power_level,
                        gold, food, wood, stone, troops
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    clan["name"], i,
                    random.choice(["defensive", "aggressive", "balanced", "cautious"]),
                    random.randint(80, 120),
                    random.randint(800, 1200),
                    random.randint(400, 600),
                    random.randint(200, 400),
                    random.randint(100, 300),
                    random.randint(40, 60)
                ))
        
        self.conn.commit()
        logger.info(f"🤖 Created AI for {len(self.config.CLANS) - len(occupied_clans)} empty clans")
    
    def is_user_verified(self, user_id: int) -> bool:
        """بررسی تأیید بودن کاربر"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ? AND is_active = 1", (user_id,))
        return cursor.fetchone() is not None
    
    def get_user_data(self, user_id: int) -> dict:
        """دریافت اطلاعات کامل کاربر"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                u.*, 
                a.name as alliance_name,
                a.alliance_id
            FROM users u
            LEFT JOIN alliance_members am ON u.user_id = am.user_id
            LEFT JOIN alliances a ON am.alliance_id = a.alliance_id
            WHERE u.user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {}
    
    def add_new_user(self, user_id: int, clan_index: int, registered_by: int) -> dict:
        """افزودن کاربر جدید به سیستم"""
        try:
            # بررسی وجود کاربر
            if self.is_user_verified(user_id):
                return {"success": False, "message": "این کاربر قبلاً ثبت شده است."}
            
            # بررسی اشغال بودن قبیله
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE clan_index = ? AND is_active = 1", (clan_index,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                return {"success": False, "message": "این قبیله قبلاً توسط کاربر دیگری انتخاب شده است."}
            
            # اطلاعات قبیله
            clan_data = self.config.CLANS[clan_index]
            clan_name = clan_data["name"]
            
            # تولید کد دعوت منحصر به فرد
            import hashlib
            invite_hash = hashlib.md5(f"{user_id}{clan_name}{datetime.now()}".encode()).hexdigest()[:8].upper()
            invite_code = f"{clan_name[:2]}{invite_hash}"
            
            # ثبت کاربر در دیتابیس
            cursor.execute('''
                INSERT INTO users (
                    user_id, clan_name, clan_index, 
                    level, power,
                    gold, food, wood, stone, troops,
                    invite_code, registered_by, registered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, clan_name, clan_index,
                self.config.INITIAL_RESOURCES["level"],
                self.config.INITIAL_RESOURCES["power"],
                self.config.INITIAL_RESOURCES["gold"],
                self.config.INITIAL_RESOURCES["food"],
                self.config.INITIAL_RESOURCES["wood"],
                self.config.INITIAL_RESOURCES["stone"],
                self.config.INITIAL_RESOURCES["troops"],
                invite_code, registered_by, datetime.now().isoformat()
            ))
            
            # حذف AI این قبیله (اگر وجود داشت)
            cursor.execute("DELETE FROM ai_clans WHERE clan_index = ?", (clan_index,))
            
            self.conn.commit()
            
            return {
                "success": True,
                "clan_name": clan_name,
                "invite_code": invite_code,
                "user_id": user_id
            }
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error adding user: {e}")
            return {"success": False, "message": "خطای یکتایی: احتمالاً کد دعوت تکراری است."}
        except Exception as e:
            logger.error(f"Error adding new user: {e}")
            return {"success": False, "message": f"خطای سیستمی: {str(e)}"}
    
    def get_stats(self):
        """دریافت آمار کلی سیستم"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        active_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT clan_index) FROM users WHERE is_active = 1")
        occupied_clans = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ai_clans")
        ai_clans = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(registered_at) FROM users")
        last_reg_row = cursor.fetchone()
        last_registration = last_reg_row[0] if last_reg_row and last_reg_row[0] else "هنوز کاربری ثبت نشده"
        
        cursor.execute("SELECT COUNT(*) FROM alliances")
        alliances_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM battles")
        battles_count = cursor.fetchone()[0]
        
        return {
            "active_users": active_users,
            "occupied_clans": occupied_clans,
            "ai_clans": ai_clans,
            "alliances_count": alliances_count,
            "battles_count": battles_count,
            "last_registration": str(last_registration)[:19]
        }
    
    def get_all_users(self):
        """دریافت لیست تمام کاربران"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                user_id, 
                COALESCE(username, 'بدون نام') as username,
                clan_name, 
                level, 
                power,
                gold,
                registered_at
            FROM users 
            WHERE is_active = 1 
            ORDER BY registered_at DESC
        ''')
        return cursor.fetchall()
    
    def get_user_stats(self, user_id: int):
        """دریافت آمار شخصی کاربر"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                wins, losses, kills,
                total_income, total_expense,
                (SELECT COUNT(*) FROM battles WHERE attacker_id = ? OR defender_id = ?) as total_battles
            FROM users 
            WHERE user_id = ?
        ''', (user_id, user_id, user_id))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {}
    
    def update_user_resources(self, user_id: int, resources: dict):
        """به‌روزرسانی منابع کاربر"""
        try:
            cursor = self.conn.cursor()
            
            # ساخت بخش SET پویا
            set_parts = []
            values = []
            
            for key, value in resources.items():
                if key in ['gold', 'food', 'wood', 'stone', 'troops', 'power']:
                    set_parts.append(f"{key} = {key} + ?")
                    values.append(value)
            
            if set_parts:
                query = f"UPDATE users SET {', '.join(set_parts)} WHERE user_id = ?"
                values.append(user_id)
                cursor.execute(query, values)
                self.conn.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating resources: {e}")
            return False
    
    def get_available_clans(self):
        """دریافت لیست قبایل خالی"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.name, c.emoji, c.title
            FROM (SELECT * FROM (
                VALUES {}
            )) AS c(name, emoji, title)
            WHERE c.name NOT IN (
                SELECT clan_name FROM users WHERE is_active = 1
            )
        '''.format(
            ','.join([f"('{clan['name']}', '{clan['emoji']}', '{clan['title']}')" for clan in self.config.CLANS])
        ))
        
        return cursor.fetchall()
    
    def get_ai_clans(self):
        """دریافت لیست قبایل AI"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT clan_name, ai_type, power_level, gold, food, troops
            FROM ai_clans
            ORDER BY power_level DESC
        ''')
        return cursor.fetchall()

