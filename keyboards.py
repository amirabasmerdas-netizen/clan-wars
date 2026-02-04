from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

class Keyboards:
    def __init__(self):
        self.config = Config()
    
    def main_menu_keyboard(self):
        """کیبورد منوی اصلی"""
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
        """کیبورد انتخاب قبیله"""
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
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("❌ لغو", callback_data="cancel")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def unverified_user_keyboard(self):
        """کیبورد برای کاربران تأیید نشده"""
        username = self.config.OWNER_USERNAME.replace('@', '')
        keyboard = [[
            InlineKeyboardButton(
                "👑 پیام به مالک",
                url=f"https://t.me/{username}"
            )
        ]]
        return InlineKeyboardMarkup(keyboard)
    
    def welcome_keyboard(self):
        """کیبورد خوش‌آمدگویی"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "📢 عضویت در کانال اخبار",
                    url=self.config.NEWS_CHANNEL
                )
            ],
            [
                InlineKeyboardButton("🎮 شروع بازی", callback_data="start_game")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def admin_panel_keyboard(self):
        """کیبورد پنل مدیریت مالک - فقط دکمه‌ای"""
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
                InlineKeyboardButton("🏠 بازگشت", callback_data="back_to_main")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
