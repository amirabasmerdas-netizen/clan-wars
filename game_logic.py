import random
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GameLogic:
    def __init__(self, db):
        self.db = db
    
    def calculate_daily_resources(self, country_id):
        """محاسبه منابع روزانه برای یک کشور"""
        country = self.db.get_country_by_id(country_id)
        if not country:
            return None
        
        # تعیین تولید روزانه بر اساس نام کشور
        country_name = country['name']
        
        productions = {
            'هخامنشیان': {'gold': 80, 'iron': 40, 'stone': 30, 'food': 60},
            'رومیان': {'gold': 60, 'iron': 80, 'stone': 50, 'food': 50},
            'مغول‌ها': {'gold': 40, 'iron': 60, 'stone': 20, 'food': 80},
            'اسپارتان‌ها': {'gold': 50, 'iron': 70, 'stone': 40, 'food': 40},
            'وایکینگ‌ها': {'gold': 70, 'iron': 50, 'stone': 30, 'food': 70},
            'سامورایی‌ها': {'gold': 65, 'iron': 60, 'stone': 35, 'food': 55},
            'مصریان': {'gold': 90, 'iron': 30, 'stone': 45, 'food': 60},
            'عثمانی‌ها': {'gold': 70, 'iron': 70, 'stone': 40, 'food': 50},
            'مایاها': {'gold': 50, 'iron': 40, 'stone': 70, 'food': 60},
            'بریتانیا': {'gold': 75, 'iron': 50, 'stone': 30, 'food': 70},
            'فرانک‌ها': {'gold': 60, 'iron': 80, 'stone': 40, 'food': 40},
            'چینی‌ها': {'gold': 70, 'iron': 50, 'stone': 80, 'food': 60}
        }
        
        if country_name in productions:
            return productions[country_name]
        
        # مقدار پیش‌فرض
        return {'gold': 50, 'iron': 40, 'stone': 30, 'food': 50}
    
    def can_collect_resources(self, country_id):
        """بررسی امکان جمع‌آوری منابع"""
        country = self.db.get_country_by_id(country_id)
        if not country:
            return False
        
        last_collected = country.get('last_collected')
        if not last_collected:
            return True
        
        # تبدیل به datetime
        if isinstance(last_collected, str):
            try:
                last_collected = datetime.fromisoformat(last_collected.replace('Z', '+00:00'))
            except:
                return True
        
        # بررسی ۲۴ ساعت گذشته
        time_since_last = datetime.now() - last_collected
        return time_since_last >= timedelta(hours=24)
    
    def collect_resources(self, country_id):
        """جمع‌آوری منابع روزانه"""
        if not self.can_collect_resources(country_id):
            return {'success': False, 'message': 'هنوز ۲۴ ساعت از جمع‌آوری قبلی نگذشته است.'}
        
        daily_resources = self.calculate_daily_resources(country_id)
        if not daily_resources:
            return {'success': False, 'message': 'کشور یافت نشد.'}
        
        # به‌روزرسانی منابع
        success = self.db.update_country_resources(country_id, daily_resources)
        if success:
            # به‌روزرسانی زمان آخرین جمع‌آوری
            cursor = self.db.conn.cursor()
            cursor.execute('''
                UPDATE countries 
                SET last_collected = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (country_id,))
            self.db.conn.commit()
            
            return {
                'success': True,
                'message': 'منابع با موفقیت جمع‌آوری شد.',
                'resources': daily_resources
            }
        
        return {'success': False, 'message': 'خطا در به‌روزرسانی منابع.'}
    
    def train_army(self, country_id, count=10):
        """آموزش سرباز"""
        country = self.db.get_country_by_id(country_id)
        if not country:
            return {'success': False, 'message': 'کشور یافت نشد.'}
        
        # بررسی منابع کافی
        cost_gold = count * 10  # هر سرباز 10 طلا
        cost_iron = count * 5   # هر سرباز 5 آهن
        
        if country['gold'] < cost_gold or country['iron'] < cost_iron:
            return {
                'success': False,
                'message': f'منابع کافی نیست! نیاز: {cost_gold} طلا و {cost_iron} آهن'
            }
        
        # کسر منابع و افزایش ارتش
        resources = {
            'gold': -cost_gold,
            'iron': -cost_iron,
            'army': count
        }
        
        success = self.db.update_country_resources(country_id, resources)
        if success:
            return {
                'success': True,
                'message': f'{count} سرباز با موفقیت آموزش داده شدند.',
                'cost': {'gold': cost_gold, 'iron': cost_iron}
            }
        
        return {'success': False, 'message': 'خطا در آموزش سربازان.'}
    
    def upgrade_defense(self, country_id, level=5):
        """تقویت دفاع"""
        country = self.db.get_country_by_id(country_id)
        if not country:
            return {'success': False, 'message': 'کشور یافت نشد.'}
        
        # بررسی منابع کافی
        cost_gold = level * 15   # هر سطح 15 طلا
        cost_stone = level * 10  # هر سطح 10 سنگ
        
        if country['gold'] < cost_gold or country['stone'] < cost_stone:
            return {
                'success': False,
                'message': f'منابع کافی نیست! نیاز: {cost_gold} طلا و {cost_stone} سنگ'
            }
        
        # کسر منابع و افزایش دفاع
        resources = {
            'gold': -cost_gold,
            'stone': -cost_stone,
            'defense': level
        }
        
        success = self.db.update_country_resources(country_id, resources)
        if success:
            return {
                'success': True,
                'message': f'دفاع به میزان {level} واحد تقویت شد.',
                'cost': {'gold': cost_gold, 'stone': cost_stone}
            }
        
        return {'success': False, 'message': 'خطا در تقویت دفاع.'}
    
    def simulate_battle(self, attacker_id, defender_id):
        """شبیه‌سازی جنگ بین دو کشور"""
        attacker = self.db.get_country_by_id(attacker_id)
        defender = self.db.get_country_by_id(defender_id)
        
        if not attacker or not defender:
            return None
        
        logger.info(f"Simulating battle: {attacker['name']} (ID:{attacker_id}) vs {defender['name']} (ID:{defender_id})")
        
        # محاسبه قدرت
        attacker_power = (
            attacker['army'] * 1.5 +  # ارتش
            attacker['defense'] * 0.5 +  # دفاع
            random.uniform(0.8, 1.2) * 50  # شانس
        )
        
        defender_power = (
            defender['army'] * 1.0 +  # ارتش
            defender['defense'] * 2.0 +  # دفاع (مهم‌تر برای مدافع)
            random.uniform(0.8, 1.2) * 50  # شانس
        )
        
        # محاسبه نسبت قدرت
        if defender_power == 0:
            power_ratio = 10.0
        else:
            power_ratio = attacker_power / defender_power
        
        # تعیین نتیجه
        if power_ratio > 2.0:
            # پیروزی قاطع حمله‌کننده
            result = "attacker_decisive_win"
            attacker_loss_percent = random.uniform(0.05, 0.15)
            defender_loss_percent = random.uniform(0.6, 0.9)
            loot_multiplier = 0.4
            
        elif power_ratio > 1.2:
            # پیروزی حمله‌کننده
            result = "attacker_win"
            attacker_loss_percent = random.uniform(0.15, 0.25)
            defender_loss_percent = random.uniform(0.4, 0.6)
            loot_multiplier = 0.3
            
        elif power_ratio > 0.8:
            # تساوی
            result = "draw"
            attacker_loss_percent = random.uniform(0.3, 0.4)
            defender_loss_percent = random.uniform(0.3, 0.4)
            loot_multiplier = 0.0
            
        elif power_ratio > 0.5:
            # پیروزی مدافع
            result = "defender_win"
            attacker_loss_percent = random.uniform(0.4, 0.6)
            defender_loss_percent = random.uniform(0.15, 0.25)
            loot_multiplier = 0.0
            
        else:
            # پیروزی قاطع مدافع
            result = "defender_decisive_win"
            attacker_loss_percent = random.uniform(0.6, 0.9)
            defender_loss_percent = random.uniform(0.05, 0.15)
            loot_multiplier = 0.0
        
        # محاسبه تلفات
        attacker_losses = int(attacker['army'] * attacker_loss_percent)
        defender_losses = int(defender['army'] * defender_loss_percent)
        
        # محاسبه غنائم (فقط اگر حمله‌کننده برنده شد)
        if result.startswith('attacker'):
            loot_gold = int(defender['gold'] * loot_multiplier * random.uniform(0.5, 1.0))
            loot_iron = int(defender['iron'] * loot_multiplier * random.uniform(0.3, 0.7))
            loot_stone = int(defender['stone'] * loot_multiplier * random.uniform(0.3, 0.7))
            loot_food = int(defender['food'] * loot_multiplier * random.uniform(0.4, 0.8))
        else:
            loot_gold = loot_iron = loot_stone = loot_food = 0
        
        battle_result = {
            'result': result,
            'attacker_losses': attacker_losses,
            'defender_losses': defender_losses,
            'loot': {
                'gold': loot_gold,
                'iron': loot_iron,
                'stone': loot_stone,
                'food': loot_food
            },
            'power_ratio': round(power_ratio, 2),
            'attacker_power': round(attacker_power, 2),
            'defender_power': round(defender_power, 2)
        }
        
        logger.info(f"Battle result: {result}, Ratio: {power_ratio:.2f}")
        return battle_result
    
    def check_season_winner(self, season_id):
        """بررسی برنده فصل"""
        top_players = self.db.get_top_players(limit=1)
        
        if not top_players:
            return None
        
        top_player = top_players[0]
        
        # دریافت کشور بازیکن
        player_country = self.db.get_player_country(top_player['user_id'])
        if not player_country:
            return None
        
        return {
            'country_id': player_country['id'],
            'country_name': player_country['name'],
            'player_id': top_player['user_id'],
            'player_username': top_player['username'],
            'score': top_player['score'],
            'total_power': top_player['total_power']
        }
    
    def attack_country(self, attacker_id, defender_id, season_id):
        """حمله به یک کشور"""
        # شبیه‌سازی جنگ
        battle_result = self.simulate_battle(attacker_id, defender_id)
        if not battle_result:
            return {'success': False, 'message': 'خطا در شبیه‌سازی جنگ.'}
        
        # ثبت جنگ در دیتابیس
        battle_id = self.db.record_battle(
            attacker_id, defender_id, season_id,
            battle_result['result'], battle_result['loot']
        )
        
        if not battle_id:
            return {'success': False, 'message': 'خطا در ثبت جنگ.'}
        
        # اعمال تلفات به ارتش‌ها
        attacker_losses = {'army': -battle_result['attacker_losses']}
        defender_losses = {'army': -battle_result['defender_losses']}
        
        self.db.update_country_resources(attacker_id, attacker_losses)
        self.db.update_country_resources(defender_id, defender_losses)
        
        # انتقال غنائم (اگر حمله‌کننده برنده شد)
        if battle_result['result'].startswith('attacker'):
            loot = battle_result['loot']
            
            # کسر غنائم از مدافع
            defender_loss_resources = {
                'gold': -loot['gold'],
                'iron': -loot['iron'],
                'stone': -loot['stone'],
                'food': -loot['food']
            }
            self.db.update_country_resources(defender_id, defender_loss_resources)
            
            # اضافه کردن غنائم به حمله‌کننده
            attacker_gain_resources = {
                'gold': loot['gold'],
                'iron': loot['iron'],
                'stone': loot['stone'],
                'food': loot['food']
            }
            self.db.update_country_resources(attacker_id, attacker_gain_resources)
            
            # افزایش امتیاز بازیکن حمله‌کننده
            if battle_result['result'] == 'attacker_decisive_win':
                score_increase = 50
            else:
                score_increase = 30
            
            cursor = self.db.conn.cursor()
            cursor.execute('''
                UPDATE players 
                SET score = score + ?
                WHERE country_id = ?
            ''', (score_increase, attacker_id))
            self.db.conn.commit()
        
        return {
            'success': True,
            'battle_id': battle_id,
            'result': battle_result
        }
