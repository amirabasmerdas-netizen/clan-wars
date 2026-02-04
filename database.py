import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='ancient_wars.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # برای برگشت دیکشنری
        self.init_db()
    
    def init_db(self):
        """ایجاد جداول دیتابیس"""
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
                last_collected TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول بازیکنان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                country_id INTEGER UNIQUE,
                score INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                loot_gold INTEGER DEFAULT 0,
                loot_iron INTEGER DEFAULT 0,
                loot_stone INTEGER DEFAULT 0,
                loot_food INTEGER DEFAULT 0,
                battle_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attacker_country_id) REFERENCES countries(id),
                FOREIGN KEY (defender_country_id) REFERENCES countries(id),
                FOREIGN KEY (season_id) REFERENCES seasons(id)
            )
        ''')
        
        # جدول تراکنش‌های منابع
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                gold_change INTEGER DEFAULT 0,
                iron_change INTEGER DEFAULT 0,
                stone_change INTEGER DEFAULT 0,
                food_change INTEGER DEFAULT 0,
                army_change INTEGER DEFAULT 0,
                defense_change INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (country_id) REFERENCES countries(id)
            )
        ''')
        
        # درج کشورهای اولیه اگر وجود ندارند
        cursor.execute('SELECT COUNT(*) FROM countries')
        if cursor.fetchone()[0] == 0:
            self.create_initial_countries()
        
        self.conn.commit()
        logger.info("✅ Database initialized successfully")
    
    def create_initial_countries(self):
        """ایجاد ۱۲ کشور باستانی"""
        countries = [
            (1, 'هخامنشیان', 'جاده شاهی', 'طلایی', 100, 80, 70, 120),
            (2, 'رومیان', 'لژیون‌ها', 'قرمز', 90, 100, 80, 90),
            (3, 'مغول‌ها', 'سواران مغول', 'آبی', 80, 70, 60, 150),
            (4, 'اسپارتان‌ها', 'فالانژ', 'نقره‌ای', 70, 90, 100, 70),
            (5, 'وایکینگ‌ها', 'کشتی‌های دراز', 'آبی تیره', 85, 80, 70, 110),
            (6, 'سامورایی‌ها', 'کاتانا', 'قرمز تیره', 95, 85, 75, 85),
            (7, 'مصریان', 'اهرام', 'طلایی روشن', 110, 60, 90, 100),
            (8, 'عثمانی‌ها', 'توپخانه', 'سبز', 80, 100, 85, 95),
            (9, 'مایاها', 'تقویم', 'قهوه‌ای', 75, 65, 110, 80),
            (10, 'بریتانیا', 'نیروی دریایی', 'آبی روشن', 100, 75, 65, 105),
            (11, 'فرانک‌ها', 'شوالیه‌ها', 'آبی خاکستری', 85, 95, 80, 90),
            (12, 'چینی‌ها', 'دیوار بزرگ', 'قرمز روشن', 90, 80, 120, 100)
        ]
        
        cursor = self.conn.cursor()
        for country in countries:
            country_id, name, special, color, army, defense, stone, food = country
            cursor.execute('''
                INSERT INTO countries 
                (id, name, special_resource, color, army, defense, stone, food) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (country_id, name, special, color, army, defense, stone, food))
        
        self.conn.commit()
        logger.info(f"✅ Created {len(countries)} initial countries")
    
    def get_available_countries(self):
        """دریافت کشورهای آزاد (بدون بازیکن)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, special_resource, color 
            FROM countries 
            WHERE controller = 'AI' AND player_id IS NULL
            ORDER BY id
        ''')
        return cursor.fetchall()
    
    def get_all_countries(self):
        """دریافت همه کشورها با اطلاعات کامل"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                c.*,
                p.username as player_username,
                p.user_id as player_user_id
            FROM countries c
            LEFT JOIN players p ON c.id = p.country_id
            ORDER BY c.id
        ''')
        return cursor.fetchall()
    
    def get_country_by_id(self, country_id):
        """دریافت کشور بر اساس ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM countries WHERE id = ?', (country_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_player_country(self, user_id):
        """دریافت کشور بازیکن"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.* FROM countries c
            JOIN players p ON c.id = p.country_id
            WHERE p.user_id = ? AND p.is_active = 1
        ''', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def add_player(self, user_id, username, country_id):
        """اضافه کردن بازیکن جدید"""
        try:
            cursor = self.conn.cursor()
            
            # بررسی وجود بازیکن
            cursor.execute('SELECT 1 FROM players WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                return {'success': False, 'message': 'این بازیکن قبلاً ثبت شده است.'}
            
            # بررسی اشغال نبودن کشور
            cursor.execute('SELECT controller, player_id FROM countries WHERE id = ?', (country_id,))
            country = cursor.fetchone()
            
            if not country:
                return {'success': False, 'message': 'کشور مورد نظر وجود ندارد.'}
            
            if country['controller'] != 'AI' or country['player_id'] is not None:
                return {'success': False, 'message': 'این کشور قبلاً اشغال شده است.'}
            
            # ثبت بازیکن
            cursor.execute('''
                INSERT INTO players (user_id, username, country_id)
                VALUES (?, ?, ?)
            ''', (user_id, username, country_id))
            
            # به‌روزرسانی کنترل کشور
            cursor.execute('''
                UPDATE countries 
                SET controller = 'PLAYER', player_id = ?
                WHERE id = ?
            ''', (user_id, country_id))
            
            # ثبت تراکنش
            cursor.execute('''
                INSERT INTO resource_transactions 
                (country_id, transaction_type, description)
                VALUES (?, 'PLAYER_JOINED', ?)
            ''', (country_id, f'بازیکن {username} کشور را گرفت'))
            
            self.conn.commit()
            return {'success': True, 'message': 'بازیکن با موفقیت ثبت شد.'}
            
        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity error adding player: {e}")
            return {'success': False, 'message': 'خطای یکتایی در ثبت بازیکن.'}
        except Exception as e:
            logger.error(f"Error adding player: {e}")
            return {'success': False, 'message': f'خطای سیستمی: {str(e)}'}
    
    def get_active_season(self):
        """دریافت فصل فعال"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM seasons WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def start_season(self, season_number):
        """شروع فصل جدید"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO seasons (season_number, is_active)
                VALUES (?, 1)
            ''', (season_number,))
            season_id = cursor.lastrowid
            self.conn.commit()
            return season_id
        except Exception as e:
            logger.error(f"Error starting season: {e}")
            return None
    
    def end_season(self, season_id, winner_country_id, winner_player_id):
        """پایان دادن به فصل"""
        try:
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
            return True
        except Exception as e:
            logger.error(f"Error ending season: {e}")
            return False
    
    def reset_game(self):
        """ریست کامل بازی"""
        try:
            cursor = self.conn.cursor()
            
            # غیرفعال کردن همه بازیکنان
            cursor.execute('UPDATE players SET is_active = 0')
            
            # پایان دادن به همه فصل‌های فعال
            cursor.execute('UPDATE seasons SET is_active = 0 WHERE is_active = 1')
            
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
                    defense = 50,
                    last_collected = NULL
                WHERE controller = 'PLAYER'
            ''')
            
            # حذف جنگ‌ها
            cursor.execute('DELETE FROM battles')
            
            # حذف تراکنش‌ها
            cursor.execute('DELETE FROM resource_transactions')
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error resetting game: {e}")
            return False
    
    def update_country_resources(self, country_id, resources):
        """به‌روزرسانی منابع کشور"""
        try:
            cursor = self.conn.cursor()
            
            # ساخت query پویا
            updates = []
            values = []
            
            for key, value in resources.items():
                if key in ['gold', 'iron', 'stone', 'food', 'army', 'defense']:
                    updates.append(f"{key} = {key} + ?")
                    values.append(value)
            
            if updates:
                query = f"UPDATE countries SET {', '.join(updates)} WHERE id = ?"
                values.append(country_id)
                cursor.execute(query, values)
                
                # ثبت تراکنش
                desc = f"تغییر منابع: {', '.join([f'{k}: {v}' for k, v in resources.items()])}"
                cursor.execute('''
                    INSERT INTO resource_transactions 
                    (country_id, transaction_type, description, gold_change, iron_change, 
                     stone_change, food_change, army_change, defense_change)
                    VALUES (?, 'RESOURCE_UPDATE', ?, ?, ?, ?, ?, ?, ?)
                ''', (country_id, desc, 
                     resources.get('gold', 0), resources.get('iron', 0),
                     resources.get('stone', 0), resources.get('food', 0),
                     resources.get('army', 0), resources.get('defense', 0)))
                
                self.conn.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating resources: {e}")
            return False
    
    def record_battle(self, attacker_id, defender_id, season_id, result, loot):
        """ثبت جنگ در دیتابیس"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO battles 
                (attacker_country_id, defender_country_id, season_id, result,
                 loot_gold, loot_iron, loot_stone, loot_food)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (attacker_id, defender_id, season_id, result,
                 loot.get('gold', 0), loot.get('iron', 0),
                 loot.get('stone', 0), loot.get('food', 0)))
            
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error recording battle: {e}")
            return None
    
    def get_player_stats(self, user_id):
        """دریافت آمار بازیکن"""
        cursor = self.conn.cursor()
        
        # تعداد جنگ‌ها
        cursor.execute('''
            SELECT 
                COUNT(*) as total_battles,
                SUM(CASE WHEN b.attacker_country_id = c.id AND b.result = 'attacker_win' THEN 1 ELSE 0 END) as attack_wins,
                SUM(CASE WHEN b.defender_country_id = c.id AND b.result = 'defender_win' THEN 1 ELSE 0 END) as defense_wins
            FROM countries c
            LEFT JOIN battles b ON c.id = b.attacker_country_id OR c.id = b.defender_country_id
            WHERE c.player_id = ?
            GROUP BY c.id
        ''', (user_id,))
        
        stats = cursor.fetchone()
        if stats:
            return dict(stats)
        return {'total_battles': 0, 'attack_wins': 0, 'defense_wins': 0}
    
    def get_top_players(self, limit=10):
        """دریافت برترین بازیکنان"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                p.user_id,
                p.username,
                c.name as country_name,
                p.score,
                (c.gold + c.iron * 2 + c.stone + c.food * 0.5 + c.army * 3 + c.defense * 2) as total_power
            FROM players p
            JOIN countries c ON p.country_id = c.id
            WHERE p.is_active = 1
            ORDER BY p.score DESC, total_power DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
