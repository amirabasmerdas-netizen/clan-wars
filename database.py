import sqlite3
from datetime import datetime
from config import DATABASE_PATH, ANCIENT_COUNTRIES, BASE_RESOURCES

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self.create_tables()
        self.initialize_countries()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # جدول بازیکنان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                country_id INTEGER,
                is_ai BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                join_date TIMESTAMP,
                FOREIGN KEY (country_id) REFERENCES countries(id)
            )
        ''')
        
        # جدول کشورها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                special_resource TEXT,
                color TEXT,
                controller TEXT DEFAULT 'AI', -- 'HUMAN' or 'AI'
                player_id INTEGER,
                gold INTEGER DEFAULT 100,
                iron INTEGER DEFAULT 100,
                stone INTEGER DEFAULT 100,
                food INTEGER DEFAULT 100,
                army INTEGER DEFAULT 50,
                defense INTEGER DEFAULT 50,
                created_at TIMESTAMP,
                last_updated TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(user_id)
            )
        ''')
        
        # جدول فصل‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_number INTEGER,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                winner_country_id INTEGER,
                winner_player_id INTEGER,
                is_active BOOLEAN DEFAULT 0,
                FOREIGN KEY (winner_country_id) REFERENCES countries(id),
                FOREIGN KEY (winner_player_id) REFERENCES players(user_id)
            )
        ''')
        
        # جدول رویدادها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER,
                event_type TEXT, -- 'WAR', 'ALLIANCE', 'TREASON', 'RESOURCE_CHANGE'
                from_country_id INTEGER,
                to_country_id INTEGER,
                description TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (season_id) REFERENCES seasons(id),
                FOREIGN KEY (from_country_id) REFERENCES countries(id),
                FOREIGN KEY (to_country_id) REFERENCES countries(id)
            )
        ''')
        
        self.conn.commit()
    
    def initialize_countries(self):
        cursor = self.conn.cursor()
        
        # ابتدا کشورهای قدیمی را حذف کنیم
        cursor.execute('DELETE FROM countries')
        
        for country in ANCIENT_COUNTRIES:
            cursor.execute('''
                INSERT INTO countries 
                (id, name, special_resource, color, controller, created_at, last_updated)
                VALUES (?, ?, ?, ?, 'AI', ?, ?)
            ''', (
                country['id'],
                country['name'],
                country['special_resource'],
                country['color'],
                datetime.now(),
                datetime.now()
            ))
        
        self.conn.commit()
    
    def add_player(self, user_id, username, country_id=None):
        cursor = self.conn.cursor()
        
        if country_id:
            # بررسی اینکه کشور قبلاً اشغال نشده باشد
            cursor.execute('''
                SELECT controller FROM countries WHERE id = ?
            ''', (country_id,))
            country = cursor.fetchone()
            
            if country and country[0] != 'AI':
                return False
            
            # اختصاص کشور به بازیکن
            cursor.execute('''
                UPDATE countries 
                SET controller = 'HUMAN', player_id = ?, last_updated = ?
                WHERE id = ? AND controller = 'AI'
            ''', (user_id, datetime.now(), country_id))
            
            if cursor.rowcount == 0:
                return False
        
        # اضافه کردن یا به‌روزرسانی بازیکن
        cursor.execute('''
            INSERT OR REPLACE INTO players 
            (user_id, username, country_id, is_ai, join_date)
            VALUES (?, ?, ?, 0, ?)
        ''', (user_id, username, country_id, datetime.now()))
        
        self.conn.commit()
        return True
    
    def get_available_countries(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, special_resource 
            FROM countries 
            WHERE controller = 'AI'
            ORDER BY name
        ''')
        return cursor.fetchall()
    
    def get_player_country(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.* FROM countries c
            JOIN players p ON c.id = p.country_id
            WHERE p.user_id = ? AND p.is_ai = 0
        ''', (user_id,))
        return cursor.fetchone()
    
    def get_all_countries(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.*, 
                   CASE 
                     WHEN c.controller = 'AI' THEN 'AI'
                     ELSE COALESCE(p.username, 'بدون بازیکن')
                   END as controller_name
            FROM countries c
            LEFT JOIN players p ON c.player_id = p.user_id
            ORDER BY c.id
        ''')
        return cursor.fetchall()
    
    def start_season(self, season_number):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO seasons 
            (season_number, start_date, is_active)
            VALUES (?, ?, 1)
        ''', (season_number, datetime.now()))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def end_season(self, season_id, winner_country_id, winner_player_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE seasons 
            SET end_date = ?, 
                winner_country_id = ?,
                winner_player_id = ?,
                is_active = 0
            WHERE id = ?
        ''', (datetime.now(), winner_country_id, winner_player_id, season_id))
        
        self.conn.commit()
    
    def get_active_season(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM seasons 
            WHERE is_active = 1 
            ORDER BY start_date DESC 
            LIMIT 1
        ''')
        return cursor.fetchone()
    
    def update_country_resources(self, country_id, resources):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE countries 
            SET gold = ?, iron = ?, stone = ?, food = ?, last_updated = ?
            WHERE id = ?
        ''', (
            resources.get('gold', 0),
            resources.get('iron', 0),
            resources.get('stone', 0),
            resources.get('food', 0),
            datetime.now(),
            country_id
        ))
        
        self.conn.commit()
    
    def get_country_by_id(self, country_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM countries WHERE id = ?', (country_id,))
        return cursor.fetchone()
    
    def reset_game(self):
        cursor = self.conn.cursor()
        
        # پایان دادن به فصل فعال
        cursor.execute('''
            UPDATE seasons 
            SET is_active = 0, end_date = ?
            WHERE is_active = 1
        ''', (datetime.now(),))
        
        # حذف بازیکنان
        cursor.execute('DELETE FROM players')
        
        # ریست کشورها
        cursor.execute('''
            UPDATE countries 
            SET controller = 'AI', 
                player_id = NULL,
                gold = 100,
                iron = 100,
                stone = 100,
                food = 100,
                army = 50,
                defense = 50,
                last_updated = ?
        ''', (datetime.now(),))
        
        # حذف رویدادها
        cursor.execute('DELETE FROM events')
        
        self.conn.commit()
        return True
    
    def add_event(self, season_id, event_type, from_country_id, to_country_id, description):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO events 
            (season_id, event_type, from_country_id, to_country_id, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (season_id, event_type, from_country_id, to_country_id, description, datetime.now()))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_player_by_id(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def remove_player(self, user_id):
        cursor = self.conn.cursor()
        
        # آزاد کردن کشور بازیکن
        cursor.execute('''
            UPDATE countries 
            SET controller = 'AI', player_id = NULL
            WHERE player_id = ?
        ''', (user_id,))
        
        # حذف بازیکن
        cursor.execute('DELETE FROM players WHERE user_id = ?', (user_id,))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_season_history(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT s.*, c.name as winner_country_name
            FROM seasons s
            LEFT JOIN countries c ON s.winner_country_id = c.id
            ORDER BY s.start_date DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def update_country_military(self, country_id, army_size=None, defense_level=None):
        cursor = self.conn.cursor()
        
        update_fields = []
        params = []
        
        if army_size is not None:
            update_fields.append("army = ?")
            params.append(army_size)
        
        if defense_level is not None:
            update_fields.append("defense = ?")
            params.append(defense_level)
        
        if not update_fields:
            return False
        
        update_fields.append("last_updated = ?")
        params.append(datetime.now())
        params.append(country_id)
        
        query = f'''
            UPDATE countries 
            SET {', '.join(update_fields)}
            WHERE id = ?
        '''
        
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.rowcount > 0
    
    def close(self):
        self.conn.close()
