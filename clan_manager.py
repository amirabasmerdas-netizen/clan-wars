import random
from datetime import datetime
from config import Config

class ClanManager:
    def __init__(self):
        self.config = Config()
    
    def get_clan_title(self, clan_name: str) -> str:
        """دریافت لقب قبیله"""
        for clan in self.config.CLANS:
            if clan["name"] == clan_name:
                return clan["title"]
        return "رهبر"
    
    def get_clan_emoji(self, clan_name: str) -> str:
        """دریافت ایموجی قبیله"""
        for clan in self.config.CLANS:
            if clan["name"] == clan_name:
                return clan["emoji"]
        return "👑"
    
    def get_clan_specialty(self, clan_name: str) -> str:
        """دریافت تخصص قبیله"""
        for clan in self.config.CLANS:
            if clan["name"] == clan_name:
                return clan.get("specialty", "بدون تخصص خاص")
        return "بدون تخصص خاص"
    
    def get_clan_description(self, clan_name: str) -> str:
        """دریافت توضیحات قبیله"""
        descriptions = {
            "هخامنشیان": "امپراتوری بزرگ با سازماندهی بی‌نظیر و جاده‌های گسترده",
            "رومیان": "قدرت نظامی منظم با لژیون‌های آموزش‌دیده",
            "مغول‌ها": "سوارکاران سریع و بی‌رحم با تاکتیک‌های برق‌آسا",
            "اسپارتان‌ها": "مدافعان سرسخت با روحیه‌ای فولادین",
            "وایکینگ‌ها": "جنگجویان دریا با کشتی‌های سریع",
            "سامورایی‌ها": "شمشیرزمان ماهر با اصول سخت‌گیرانه",
            "مصریان": "تمدن ثروتمند با اهرام و معابد باشکوه",
            "عثمانی‌ها": "فاتحان با توپخانه قدرتمند",
            "مایاها": "تمدن رازآلود با دانش نجوم پیشرفته",
            "بریتانیا": "قدرت دریایی با ناوگان گسترده",
            "فرانک‌ها": "شوالیه‌های زره‌پوش با روحیه‌ای جنگجو",
            "چینی‌ها": "تمدن کهن با اختراعات و جمعیت زیاد"
        }
        return descriptions.get(clan_name, "قبیله باستانی با تاریخ غنی")
    
    def get_clan_bonuses(self, clan_name: str) -> dict:
        """دریافت امتیازات ویژه هر قبیله"""
        bonuses = {
            "هخامنشیان": {"gold_income": 1.2, "defense": 1.1, "movement_speed": 0.9},
            "رومیان": {"troop_training": 1.3, "defense": 1.2, "gold_income": 0.9},
            "مغول‌ها": {"movement_speed": 1.4, "attack": 1.1, "defense": 0.8},
            "اسپارتان‌ها": {"defense": 1.5, "troop_health": 1.2, "movement_speed": 0.7},
            "وایکینگ‌ها": {"naval_power": 1.4, "attack": 1.1, "gold_income": 1.1},
            "سامورایی‌ها": {"attack": 1.3, "troop_accuracy": 1.2, "defense": 1.0},
            "مصریان": {"gold_income": 1.4, "food_production": 1.2, "attack": 0.9},
            "عثمانی‌ها": {"siege_power": 1.3, "defense": 1.1, "gold_income": 1.0},
            "مایاها": {"research_speed": 1.3, "defense": 1.0, "attack": 1.0},
            "بریتانیا": {"naval_power": 1.5, "gold_income": 1.2, "defense": 0.9},
            "فرانک‌ها": {"cavalry_power": 1.4, "defense": 1.1, "movement_speed": 0.9},
            "چینی‌ها": {"population_growth": 1.3, "research_speed": 1.2, "gold_income": 1.1}
        }
        return bonuses.get(clan_name, {"attack": 1.0, "defense": 1.0, "gold_income": 1.0})
    
    def calculate_battle_result(self, attacker_clan: str, defender_clan: str, 
                                attacker_power: int, defender_power: int) -> dict:
        """محاسبه نتیجه نبرد بین دو قبیله"""
        
        # دریافت امتیازات ویژه
        attacker_bonus = self.get_clan_bonuses(attacker_clan)
        defender_bonus = self.get_clan_bonuses(defender_clan)
        
        # اعمال امتیازات
        attacker_effective_power = attacker_power * attacker_bonus.get('attack', 1.0)
        defender_effective_power = defender_power * defender_bonus.get('defense', 1.0)
        
        # شانس تصادفی
        random_factor = random.uniform(0.8, 1.2)
        
        # محاسبه نسبت قدرت
        if defender_effective_power == 0:
            power_ratio = 10.0
        else:
            power_ratio = attacker_effective_power / defender_effective_power * random_factor
        
        # تعیین نتیجه
        if power_ratio > 2.0:
            result = "decisive_victory"  # پیروزی قاطع
            attacker_loss_percent = random.uniform(0.05, 0.15)
            defender_loss_percent = random.uniform(0.6, 0.9)
        elif power_ratio > 1.2:
            result = "victory"  # پیروزی
            attacker_loss_percent = random.uniform(0.15, 0.25)
            defender_loss_percent = random.uniform(0.4, 0.6)
        elif power_ratio > 0.8:
            result = "draw"  # تساوی
            attacker_loss_percent = random.uniform(0.3, 0.4)
            defender_loss_percent = random.uniform(0.3, 0.4)
        elif power_ratio > 0.5:
            result = "defeat"  # شکست
            attacker_loss_percent = random.uniform(0.4, 0.6)
            defender_loss_percent = random.uniform(0.15, 0.25)
        else:
            result = "decisive_defeat"  # شکست سنگین
            attacker_loss_percent = random.uniform(0.6, 0.9)
            defender_loss_percent = random.uniform(0.05, 0.15)
        
        # محاسبه تلفات
        attacker_losses = int(attacker_power * attacker_loss_percent)
        defender_losses = int(defender_power * defender_loss_percent)
        
        # محاسبه غنائم
        if result in ["victory", "decisive_victory"]:
            loot_multiplier = 0.3 if result == "victory" else 0.5
            gold_loot = int(defender_power * loot_multiplier * random.uniform(0.8, 1.2))
            food_loot = int(defender_power * loot_multiplier * random.uniform(0.6, 1.0))
        else:
            gold_loot = 0
            food_loot = 0
        
        return {
            "result": result,
            "attacker_losses": attacker_losses,
            "defender_losses": defender_losses,
            "gold_loot": gold_loot,
            "food_loot": food_loot,
            "power_ratio": round(power_ratio, 2)
        }
    
    def get_ai_decision(self, ai_type: str, situation: str) -> str:
        """دریافت تصمیم AI بر اساس نوع و موقعیت"""
        decisions = {
            "defensive": {
                "under_attack": "defend",
                "weak_enemy": "defend",
                "strong_enemy": "defend",
                "neutral": "build",
                "resource_rich": "defend"
            },
            "aggressive": {
                "under_attack": "counter_attack",
                "weak_enemy": "attack",
                "strong_enemy": "raid",
                "neutral": "scout",
                "resource_rich": "attack"
            },
            "balanced": {
                "under_attack": "defend_if_stronger",
                "weak_enemy": "attack_if_safe",
                "strong_enemy": "ally_if_possible",
                "neutral": "trade",
                "resource_rich": "expand"
            },
            "cautious": {
                "under_attack": "retreat",
                "weak_enemy": "attack_cautiously",
                "strong_enemy": "avoid",
                "neutral": "observe",
                "resource_rich": "fortify"
            }
        }
        
        return decisions.get(ai_type, {}).get(situation, "wait")
