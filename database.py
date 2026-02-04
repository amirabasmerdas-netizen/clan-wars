import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='ancient_wars.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        
        # جدول کشورها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                special_resource TEXT,
                color TEXT,
                controller TEXT DEFAULT 'AI',
                player_id INTEGER,
                gold INTEGER DEFAULT 1000,
                iron INTEGER DEFAULT 500,
                stone INTEGER DEFAULT 300,
                food INTEGER DEFAULT 800,
                army INTEGER DEFAULT 100,
                defense INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول بازیکنان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                country_id INTEGER,
                score INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (country_id) REFERENCES countries(id)
            )
        ''')
        
        # جدول فصل‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_number INTEGER NOT NULL,
                winner_country_id INTEGER,
                winner_player_id INTEGER,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # جدول جنگ‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_country_id INTEGER,
                defender_country_id INTEGER,
                season_id INTEGER,
                result TEXT,
                loot_gold INTEGER,
                loot_iron INTEGER,
                battle_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attacker_country_id) REFERENCES countries(id),
                FOREIGN KEY (defender_country_id) REFERENCES countries(id)
            )
        ''')
        
        # درج کشورهای اولیه اگر وجود ندارند
        cursor.execute('SELECT COUNT(*) FROM countries')
        if cursor.fetchone()[0] == 0:
            self.create_initial_countries()
        
        self.conn.commit()
        logger.info("Database initialized")
    
    def create_initial_countries(self):
        """ایجاد ۱۲ کشور باستانی"""
        countries = [
            (1, 'هخامنشیان', 'جاده شاهی', 'طلا'),
            (2, 'رومیان', 'لژیون‌ها', 'قرمز'),
            (3, 'مغول‌ها', 'سواران مغول', 'آبی'),
            (4, 'اسپارتان‌ها', 'فالانژ', 'نقره‌ای'),
            (5, 'وایکینگ‌ها', 'کشتی‌های دراز', 'آبی تیره'),
            (6, 'سامورایی‌ها', 'کاتانا', 'قرمز'),
            (7, 'مصریان', 'اهرام', 'طلایی'),
            (8, 'عثمانی‌ها', 'توپخانه', 'سبز'),
            (9, 'مایاها', 'تقویم', 'قهوه‌ای'),
            (10, 'بریتانیا', 'نیروی دریایی', 'آبی'),
            (11, 'فرانک‌ها', 'شوالیه‌ها', 'آبی'),
            (12, 'چینی‌ها', 'دیوار بزرگ', 'قرمز')
        ]
        
        cursor = self.conn.cursor()
        for country in countries:
            cursor.execute('''
                INSERT INTO countries (id, name, special_resource, color) 
                VALUES (?, ?, ?, ?)
            ''', country)
        
        self.conn.commit()
    
    def get_available_countries(self):
        """دریافت کشورهای آزاد"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name FROM countries 
            WHERE controller = 'AI' 
            ORDER BY id
        ''')
        return cursor.fetchall()
    
    def get_all_countries(self):
        """دریافت همه کشورها"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM countries ORDER BY id')
        return cursor.fetchall()
    
    def get_country_by_id(self, country_id):
        """دریافت کشور بر اساس ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM countries WHERE id = ?', (country_id,))
        return cursor.fetchone()
    
    def get_player_country(self, user_id):
        """دریافت کشور بازیکن"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.* FROM countries c
            JOIN players p ON c.id = p.country_id
            WHERE p.user_id = ? AND p.is_active = 1
        ''', (user_id,))
        return cursor.fetchone()
    
    def add_player(self, user_id, username, country_id):
        """اضافه کردن بازیکن جدید"""
        try:
            cursor = self.conn.cursor()
            
            # بررسی اشغال نبودن کشور
            cursor.execute('SELECT controller FROM countries WHERE id = ?', (country_id,))
            country = cursor.fetchone()
            
            if not country or country[0] != 'AI':
                return False
            
            # ثبت بازیکن
            cursor.execute('''
                INSERT OR REPLACE INTO players (user_id, username, country_id)
                VALUES (?, ?, ?)
            ''', (user_id, username, country_id))
            
            # به‌روزرسانی کنترل کشور
            cursor.execute('''
                UPDATE countries 
                SET controller = 'PLAYER', player_id = ?
                WHERE id = ?
            ''', (user_id, country_id))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding player: {e}")
            return False
    
    def get_active_season(self):
        """دریافت فصل فعال"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM seasons WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
        return cursor.fetchone()
    
    def start_season(self, season_number):
        """شروع فصل جدید"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO seasons (season_number, is_active)
            VALUES (?, 1)
        ''', (season_number,))
        season_id = cursor.lastrowid
        self.conn.commit()
        return season_id
    
    def end_season(self, season_id, winner_country_id, winner_player_id):
        """پایان دادن به فصل"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE seasons 
            SET is_active = 0, 
                end_date = CURRENT_TIMESTAMP,
                winner_country_id = ?,
                winner_player_id = ?
            WHERE id = ?
        ''', (winner_country_id, winner_player_id, season_id))
        self.conn.commit()
    
    def reset_game(self):
        """ریست کامل بازی"""
        cursor = self.conn.cursor()
        
        # حذف بازیکنان
        cursor.execute('DELETE FROM players')
        
        # حذف فصل‌ها
        cursor.execute('DELETE FROM seasons')
        
        # حذف جنگ‌ها
        cursor.execute('DELETE FROM battles')
        
        # بازنشانی کشورها
        cursor.execute('''
            UPDATE countries 
            SET controller = 'AI', 
                player_id = NULL,
                gold = 1000,
                iron = 500,
                stone = 300,
                food = 800,
                army = 100,
                defense = 50
        ''')
        
        self.conn.commit()
        return True
