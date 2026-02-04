from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

class Keyboards:
    def __init__(self):
        self.config = Config()
    
    def main_menu_keyboard(self):
        """کیبورد منوی اصلی بازی"""
        keyboard = [
            [
                InlineKeyboardButton("⚔️ جنگ", callback_data="battle"),
                InlineKeyboardButton("🏗 ساخت‌وساز", callback_data="build")
            ],
            [
                InlineKeyboardButton("💰 اقتصاد", callback_data="economy"),
                InlineKeyboardButton("🤝 اتحاد", callback_data="alliance")
            ],
            [
                InlineKeyboardButton("📊 آمار", callback_data="stats"),
                InlineKeyboardButton("📖 راهنما", callback_data="guide")
            ],
            [
                InlineKeyboardButton("📢 کانال اخبار", callback_data="news_channel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def clan_selection_keyboard(self):
        """کیبورد انتخاب قبیله برای مالک"""
        keyboard = []
        clans = self.config.CLANS
        
        # نمایش قبایل در ردیف‌های ۳ تایی
        for i in range(0, len(clans), 3):
            row = []
            for j in range(3):
                if i + j < len(clans):
                    clan = clans[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"{clan['emoji']} {clan['name']}",
                            callback_data=f"clan_{i + j}"
                        )
                    )
            if row:
                keyboard.append(row)
        
        # دکمه لغو
        keyboard.append([
            InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def unverified_user_keyboard(self):
        """کیبورد برای کاربران تأیید نشده"""
        username = self.config.OWNER_USERNAME.replace('@', '')
        keyboard = [
            [
                InlineKeyboardButton(
                    "👑 پیام به مالک",
                    url=f"https://t.me/{username}"
                )
            ],
            [
                InlineKeyboardButton(
                    "ℹ️ راهنمای ثبت‌نام",
                    callback_data="registration_guide"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def welcome_keyboard(self):
        """کیبورد پیام خوش‌آمدگویی"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "📢 عضویت در کانال اخبار",
                    url=self.config.NEWS_CHANNEL
                )
            ],
            [
                InlineKeyboardButton(
                    "📖 عضویت در کانال راهنما",
                    url=self.config.GUIDE_CHANNEL
                )
            ],
            [
                InlineKeyboardButton(
                    "👥 عضویت در کانال جامعه",
                    url=self.config.COMMUNITY_CHANNEL
                )
            ],
            [
                InlineKeyboardButton("🎮 شروع بازی", callback_data="start_game"),
                InlineKeyboardButton("📚 آموزش", callback_data="tutorial")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def admin_panel_keyboard(self):
        """کیبورد پنل مدیریت مالک"""
        keyboard = [
            [
                InlineKeyboardButton("➕ افزودن کاربر", callback_data="admin_add_user"),
                InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_list_users")
            ],
            [
                InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats"),
                InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton("🔄 به‌روزرسانی AI", callback_data="admin_update_ai"),
                InlineKeyboardButton("📢 اطلاع‌رسانی", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def battle_menu_keyboard(self):
        """کیبورد منوی جنگ"""
        keyboard = [
            [
                InlineKeyboardButton("🎯 حمله", callback_data="battle_attack"),
                InlineKeyboardButton("🛡 دفاع", callback_data="battle_defend")
            ],
            [
                InlineKeyboardButton("🏹 آموزش نیرو", callback_data="battle_train"),
                InlineKeyboardButton("🗺 نقشه جهان", callback_data="battle_map")
            ],
            [
                InlineKeyboardButton("⚔️ نبردهای فعال", callback_data="battle_active"),
                InlineKeyboardButton("📜 تاریخچه جنگ‌ها", callback_data="battle_history")
            ],
            [
                InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def build_menu_keyboard(self):
        """کیبورد منوی ساخت‌وساز"""
        keyboard = [
            [
                InlineKeyboardButton("🏯 قلعه", callback_data="build_castle"),
                InlineKeyboardButton("🏹 آموزشگاه", callback_data="build_barracks")
            ],
            [
                InlineKeyboardButton("💰 بازار", callback_data="build_market"),
                InlineKeyboardButton("🌾 مزرعه", callback_data="build_farm")
            ],
            [
                InlineKeyboardButton("🪵 جنگلداری", callback_data="build_lumber"),
                InlineKeyboardButton("🪨 معدن", callback_data="build_mine")
            ],
            [
                InlineKeyboardButton("🔄 ارتقاء ساختمان", callback_data="build_upgrade"),
                InlineKeyboardButton("🗑 تخریب", callback_data="build_demolish")
            ],
            [
                InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def economy_menu_keyboard(self):
        """کیبورد منوی اقتصاد"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 تجارت", callback_data="economy_trade"),
                InlineKeyboardButton("📈 بازار", callback_data="economy_market")
            ],
            [
                InlineKeyboardButton("🏛 مالیات", callback_data="economy_tax"),
                InlineKeyboardButton("📊 گزارش", callback_data="economy_report")
            ],
            [
                InlineKeyboardButton("💰 وام", callback_data="economy_loan"),
                InlineKeyboardButton("🎁 پاداش", callback_data="economy_reward")
            ],
            [
                InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def alliance_menu_keyboard(self):
        """کیبورد منوی اتحاد"""
        keyboard = [
            [
                InlineKeyboardButton("➕ ایجاد اتحاد", callback_data="alliance_create"),
                InlineKeyboardButton("👥 پیوستن", callback_data="alliance_join")
            ],
            [
                InlineKeyboardButton("📜 لیست اتحادها", callback_data="alliance_list"),
                InlineKeyboardButton("🗣 مذاکره", callback_data="alliance_negotiate")
            ],
            [
                InlineKeyboardButton("📊 اعضای اتحاد", callback_data="alliance_members"),
                InlineKeyboardButton("⚔️ جنگ اتحاد", callback_data="alliance_battle")
            ],
            [
                InlineKeyboardButton("🏠 بازگشت به منو", callback_data="back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def back_to_main_keyboard(self):
        """کیبورد بازگشت به منوی اصلی"""
        keyboard = [[
            InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_main")
        ]]
        return InlineKeyboardMarkup(keyboard)
    
    def yes_no_keyboard(self, yes_data="yes", no_data="no"):
        """کیبورد بله/خیر"""
        keyboard = [
            [
                InlineKeyboardButton("✅ بله", callback_data=yes_data),
                InlineKeyboardButton("❌ خیر", callback_data=no_data)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def pagination_keyboard(self, current_page: int, total_pages: int, prefix: str):
        """کیبورد صفحه‌بندی"""
        keyboard = []
        
        if current_page > 1:
            keyboard.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"{prefix}_page_{current_page-1}"))
        
        keyboard.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="page_info"))
        
        if current_page < total_pages:
            keyboard.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"{prefix}_page_{current_page+1}"))
        
        return InlineKeyboardMarkup([keyboard])
