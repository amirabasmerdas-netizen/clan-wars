from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

config = Config()

class Keyboards:
    @staticmethod
    def get_main_menu(owner_id, user_id):
        """منوی اصلی"""
        keyboard = []
        
        # دکمه‌های عمومی برای همه
        keyboard.append([InlineKeyboardButton("🌍 مشاهده همه کشورها", callback_data="view_countries")])
        keyboard.append([InlineKeyboardButton("🏛️ کشور من", callback_data="my_country")])
        keyboard.append([InlineKeyboardButton("📊 منابع من", callback_data="view_resources")])
        keyboard.append([InlineKeyboardButton("⚔️ حمله به کشور", callback_data="attack_country")])
        keyboard.append([InlineKeyboardButton("🏆 رتبه‌بندی بازیکنان", callback_data="leaderboard")])
        
        # دکمه‌های مخصوص مالک
        if str(user_id) == str(owner_id):
            keyboard.append([InlineKeyboardButton("➕ افزودن بازیکن", callback_data="add_player")])
            keyboard.append([InlineKeyboardButton("🎮 شروع فصل جدید", callback_data="start_season")])
            keyboard.append([InlineKeyboardButton("🏁 پایان فصل", callback_data="end_season")])
            keyboard.append([InlineKeyboardButton("🔄 ریست کامل بازی", callback_data="reset_game")])
        
        keyboard.append([InlineKeyboardButton("📢 کانال اخبار", url=config.NEWS_CHANNEL)])
        keyboard.append([InlineKeyboardButton("❓ راهنما", callback_data="help")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_back_keyboard():
        """کیبورد بازگشت"""
        keyboard = [[
            InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main_menu")
        ]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_countries_keyboard(available_only=False, countries_list=None):
        """کیبورد انتخاب کشور"""
        keyboard = []
        
        if countries_list:
            for country_id, country_name, special_resource, color in countries_list:
                emoji = "👑" if "هخامنشی" in country_name else "🏛️"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} {country_name} ({special_resource})",
                        callback_data=f"country_{country_id}"
                    )
                ])
        else:
            # کشورهای پیش‌فرض
            countries = [
                (1, 'هخامنشیان', 'جاده شاهی', 'طلایی'),
                (2, 'رومیان', 'لژیون‌ها', 'قرمز'),
                (3, 'مغول‌ها', 'سواران مغول', 'آبی'),
                (4, 'اسپارتان‌ها', 'فالانژ', 'نقره‌ای'),
                (5, 'وایکینگ‌ها', 'کشتی‌های دراز', 'آبی تیره'),
                (6, 'سامورایی‌ها', 'کاتانا', 'قرمز تیره'),
                (7, 'مصریان', 'اهرام', 'طلایی روشن'),
                (8, 'عثمانی‌ها', 'توپخانه', 'سبز'),
                (9, 'مایاها', 'تقویم', 'قهوه‌ای'),
                (10, 'بریتانیا', 'نیروی دریایی', 'آبی روشن'),
                (11, 'فرانک‌ها', 'شوالیه‌ها', 'آبی خاکستری'),
                (12, 'چینی‌ها', 'دیوار بزرگ', 'قرمز روشن')
            ]
            
            for country_id, country_name, special_resource, color in countries:
                emoji = "👑" if "هخامنشی" in country_name else "🏛️"
                button_text = f"{emoji} {country_name}"
                
                if not available_only:
                    button_text += f" ({special_resource})"
                
                keyboard.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"country_{country_id}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_confirmation_keyboard(action_type):
        """کیبورد تأیید عملیات"""
        keyboard = [
            [
                InlineKeyboardButton("✅ بله، تأیید می‌کنم", callback_data=f"confirm_{action_type}"),
                InlineKeyboardButton("❌ خیر، لغو کن", callback_data="cancel_action")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_resource_management():
        """کیبورد مدیریت منابع"""
        keyboard = [
            [InlineKeyboardButton("💰 جمع‌آوری منابع روزانه", callback_data="collect_resources")],
            [InlineKeyboardButton("⚔️ آموزش سرباز جدید (۱۰ نفر)", callback_data="train_army")],
            [InlineKeyboardButton("🛡️ تقویت دفاع (۵ واحد)", callback_data="upgrade_defense")],
            [InlineKeyboardButton("📈 وضعیت منابع", callback_data="view_resources")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_attack_targets_keyboard(user_country_id):
        """کیبورد انتخاب هدف برای حمله"""
        keyboard = []
        
        # کشورهای مختلف برای حمله (بجز کشور خودش)
        targets = [
            (1, 'هخامنشیان'), (2, 'رومیان'), (3, 'مغول‌ها'),
            (4, 'اسپارتان‌ها'), (5, 'وایکینگ‌ها'), (6, 'سامورایی‌ها'),
            (7, 'مصریان'), (8, 'عثمانی‌ها'), (9, 'مایاها'),
            (10, 'بریتانیا'), (11, 'فرانک‌ها'), (12, 'چینی‌ها')
        ]
        
        for country_id, country_name in targets:
            if country_id != user_country_id:
                keyboard.append([
                    InlineKeyboardButton(
                        f"⚔️ حمله به {country_name}",
                        callback_data=f"attack_{country_id}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_admin_panel_keyboard():
        """کیبورد پنل مدیریت مالک"""
        keyboard = [
            [InlineKeyboardButton("➕ افزودن بازیکن جدید", callback_data="add_player")],
            [InlineKeyboardButton("📋 لیست بازیکنان", callback_data="list_players")],
            [InlineKeyboardButton("🎮 شروع فصل جدید", callback_data="start_season")],
            [InlineKeyboardButton("🏁 پایان فصل فعلی", callback_data="end_season")],
            [InlineKeyboardButton("📊 آمار کلی بازی", callback_data="game_stats")],
            [InlineKeyboardButton("🔄 ریست کامل بازی", callback_data="reset_game")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_cancel_keyboard():
        """کیبورد لغو"""
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="main_menu")]])
    
    @staticmethod
    def get_yes_no_keyboard(yes_data="yes", no_data="no"):
        """کیبورد بله/خیر عمومی"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله", callback_data=yes_data),
                InlineKeyboardButton("❌ خیر", callback_data=no_data)
            ]
        ])
