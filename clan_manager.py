import random
import logging

logger = logging.getLogger(__name__)

class GameLogic:
    def __init__(self, db):
        self.db = db
    
    def calculate_daily_resources(self, country_id):
        """محاسبه منابع روزانه برای یک کشور"""
        country = self.db.get_country_by_id(country_id)
        if not country:
            return None
        
        # محاسبه تولید روزانه بر اساس نوع کشور
        productions = {
            'هخامنشیان': {'gold': 50, 'iron': 20, 'stone': 15, 'food': 30},
            'رومیان': {'gold': 30, 'iron': 40, 'stone': 25, 'food': 25},
            'مغول‌ها': {'gold': 20, 'iron': 30, 'stone': 10, 'food': 40},
            'اسپارتان‌ها': {'gold': 25, 'iron': 35, 'stone': 20, 'food': 20},
            'وایکینگ‌ها': {'gold': 35, 'iron': 25, 'stone': 15, 'food': 25},
            'سامورایی‌ها': {'gold': 30, 'iron': 30, 'stone': 20, 'food': 20},
            'مصریان': {'gold': 60, 'iron': 15, 'stone': 25, 'food': 30},
            'عثمانی‌ها': {'gold': 40, 'iron': 35, 'stone': 20, 'food': 25},
            'مایاها': {'gold': 25, 'iron': 20, 'stone': 35, 'food': 30},
            'بریتانیا': {'gold': 45, 'iron': 25, 'stone': 15, 'food': 35},
            'فرانک‌ها': {'gold': 30, 'iron': 40, 'stone': 20, 'food': 20},
            'چینی‌ها': {'gold': 35, 'iron': 25, 'stone': 40, 'food': 30}
        }
        
        country_name = country[1]
        if country_name in productions:
            return productions[country_name]
        return {'gold': 25, 'iron': 20, 'stone': 15, 'food': 25}
    
    def check_season_winner(self, season_id):
        """بررسی برنده فصل"""
        # دریافت همه کشورهای با بازیکن
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT c.id as country_id, p.user_id as player_id, 
                   (c.gold + c.iron * 2 + c.stone + c.food * 0.5 + c.army * 3 + c.defense * 2) as score
            FROM countries c
            JOIN players p ON c.id = p.country_id
            WHERE c.controller = 'PLAYER' AND p.is_active = 1
            ORDER BY score DESC
            LIMIT 1
        ''')
        
        winner = cursor.fetchone()
        if winner:
            return {
                'country_id': winner[0],
                'player_id': winner[1],
                'score': winner[2]
            }
        return None
    
    def simulate_battle(self, attacker_id, defender_id):
        """شبیه‌سازی جنگ بین دو کشور"""
        attacker = self.db.get_country_by_id(attacker_id)
        defender = self.db.get_country_by_id(defender_id)
        
        if not attacker or not defender:
            return None
        
        # محاسبه قدرت
        attacker_power = attacker[10] * 1.5 + attacker[11]  # ارتش * 1.5 + دفاع
        defender_power = defender[11] * 2 + defender[10] * 0.5  # دفاع * 2 + ارتش * 0.5
        
        # شانس تصادفی
        random_factor = random.uniform(0.8, 1.2)
        
        # تعیین برنده
        if attacker_power * random_factor > defender_power:
            # حمله‌کننده برنده شد
            result = "attacker_win"
            
            # محاسبه غنائم (حداکثر 30٪ منابع مدافع)
            loot_gold = int(defender[6] * 0.3 * random.uniform(0.5, 1.0))
            loot_iron = int(defender[7] * 0.2 * random.uniform(0.5, 1.0))
            
            # تلفات
            attacker_loss = int(attacker[10] * 0.1)  # 10٪ تلفات
            defender_loss = int(defender[10] * 0.3)  # 30٪ تلفات
            
            return {
                'result': result,
                'loot_gold': loot_gold,
                'loot_iron': loot_iron,
                'attacker_loss': attacker_loss,
                'defender_loss': defender_loss
            }
        else:
            # مدافع برنده شد
            result = "defender_win"
            
            # تلفات
            attacker_loss = int(attacker[10] * 0.3)  # 30٪ تلفات
            defender_loss = int(defender[10] * 0.1)  # 10٪ تلفات
            
            return {
                'result': result,
                'loot_gold': 0,
                'loot_iron': 0,
                'attacker_loss': attacker_loss,
                'defender_loss': defender_loss
            }
