import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# Import internal modules
from config import Config
from database import Database
from game_logic import GameLogic
from keyboards import Keyboards

# تنظیمات
config = Config()
db = Database()
game_logic = GameLogic(db)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# وضعیت‌های مکالمه
SELECTING_COUNTRY, ENTERING_USER_ID = range(2)

# Flask app
flask_app = Flask(__name__)
application = None
bot = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start - شروع ربات"""
    user = update.effective_user
    user_id = user.id
    
    logger.info(f"User {user_id} (@{user.username}) started the bot")
    
    keyboard = Keyboards.get_main_menu(config.OWNER_ID, user_id)
    
    welcome_message = f"""
👋 سلام {user.first_name}!

🏛️ **به بازی جنگ جهانی باستان خوش آمدید!**

🕰️ در این بازی شما رهبر یک تمدن باستانی خواهید بود:
• منابع جمع‌آوری کنید
• ارتش آموزش دهید
• به کشورهای دیگر حمله کنید
• فاتح جهان باستان شوید!

👑 **مالک بازی:** {config.OWNER_USERNAME}
📢 **کانال اخبار:** @Aryaboom_News

برای شروع از دکمه‌های زیر استفاده کنید:
    """
    
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(welcome_message, reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /help - راهنمای بازی"""
    help_text = """
📖 **راهنمای بازی جنگ جهانی باستان**

🎮 **هدف بازی:**
فتح جهان باستان با توسعه کشور خود و شکست دادن دیگر کشورها

🏛️ **کشور شما:**
هر بازیکن یک کشور باستانی را کنترل می‌کند

💰 **منابع:**
• طلا: برای آموزش سرباز و تقویت دفاع
• آهن: برای آموزش سرباز
• سنگ: برای تقویت دفاع
• غذا: برای نگهداری ارتش

⚔️ **نظامی:**
• ارتش: برای حمله و دفاع
• دفاع: مقاومت در برابر حملات

🔄 **عملیات روزانه:**
1. جمع‌آوری منابع روزانه
2. آموزش سربازان جدید
3. تقویت دفاع کشور
4. حمله به کشورهای دیگر

📅 **فصل‌ها:**
هر فصل یک دوره رقابت است
برنده فصل: بازیکنی با بیشترین امتیاز

👑 **مالک بازی:** فقط مالک می‌تواند:
• بازیکن جدید اضافه کند
• فصل جدید شروع کند
• بازی را ریست کند

📞 **پشتیبانی:** برای مشکل یا سوال به @amele55 پیام دهید
    """
    
    keyboard = Keyboards.get_back_keyboard()
    await update.message.reply_text(help_text, reply_markup=keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    logger.info(f"Button clicked by {user_id}: {data}")
    
    # منوی اصلی
    if data == "main_menu":
        await start(update, context)
    
    # مشاهده همه کشورها
    elif data == "view_countries":
        countries = db.get_all_countries()
        
        if not countries:
            await query.edit_message_text(
                "⚠️ هیچ کشوری در سیستم وجود ندارد!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        message = "🌍 **فهرست کشورهای جهان باستان:**\n\n"
        
        for country in countries:
            controller = "🤖 AI" if country['controller'] == 'AI' else f"👤 {country['player_username'] or 'بازیکن'}"
            
            message += (
                f"🏛️ **{country['name']}**\n"
                f"   📍 منبع ویژه: {country['special_resource']}\n"
                f"   🎨 رنگ: {country['color']}\n"
                f"   👑 کنترل‌کننده: {controller}\n"
                f"   ⚔️ ارتش: {country['army']} | 🛡️ دفاع: {country['defense']}\n"
                f"   💰 طلا: {country['gold']} | ⚒️ آهن: {country['iron']}\n"
                f"   🪨 سنگ: {country['stone']} | 🍖 غذا: {country['food']}\n"
                f"   {'─' * 30}\n"
            )
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=Keyboards.get_back_keyboard()
        )
    
    # مشاهده کشور خود
    elif data == "my_country":
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            await query.edit_message_text(
                "⚠️ شما هنوز کشوری ندارید!\n\n"
                "برای دریافت کشور باید توسط مالک بازی تأیید شوید.\n"
                f"👑 مالک: {config.OWNER_USERNAME}\n\n"
                "لطفاً به مالک پیام دهید و درخواست کشور کنید.",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        # دریافت آمار بازیکن
        player_stats = db.get_player_stats(user_id)
        
        message = (
            f"🏛️ **کشور شما: {player_country['name']}**\n\n"
            f"✨ **مشخصات:**\n"
            f"   📍 منبع ویژه: {player_country['special_resource']}\n"
            f"   🎨 رنگ پرچم: {player_country['color']}\n\n"
            f"💰 **منابع:**\n"
            f"   💰 طلا: {player_country['gold']}\n"
            f"   ⚒️ آهن: {player_country['iron']}\n"
            f"   🪨 سنگ: {player_country['stone']}\n"
            f"   🍖 غذا: {player_country['food']}\n\n"
            f"⚔️ **نظامی:**\n"
            f"   ⚔️ ارتش: {player_country['army']}\n"
            f"   🛡️ دفاع: {player_country['defense']}\n\n"
            f"📊 **آمار شما:**\n"
            f"   🎮 تعداد جنگ‌ها: {player_stats['total_battles']}\n"
            f"   ✅ پیروزی‌های حمله: {player_stats['attack_wins']}\n"
            f"   🛡️ پیروزی‌های دفاع: {player_stats['defense_wins']}\n\n"
            f"برای مدیریت کشور از دکمه‌های زیر استفاده کنید:"
        )
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=Keyboards.get_resource_management()
        )
    
    # مشاهده منابع
    elif data == "view_resources":
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            await query.edit_message_text(
                "⚠️ شما کشوری ندارید!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        daily_resources = game_logic.calculate_daily_resources(player_country['id'])
        
        message = (
            f"📊 **وضعیت منابع {player_country['name']}**\n\n"
            f"💰 **موجودی فعلی:**\n"
            f"   💰 طلا: {player_country['gold']}\n"
            f"   ⚒️ آهن: {player_country['iron']}\n"
            f"   🪨 سنگ: {player_country['stone']}\n"
            f"   🍖 غذا: {player_country['food']}\n\n"
        )
        
        if daily_resources:
            message += (
                f"🔄 **تولید روزانه:**\n"
                f"   💰 طلا: +{daily_resources['gold']}\n"
                f"   ⚒️ آهن: +{daily_resources['iron']}\n"
                f"   🪨 سنگ: +{daily_resources['stone']}\n"
                f"   🍖 غذا: +{daily_resources['food']}\n\n"
            )
        
        can_collect = game_logic.can_collect_resources(player_country['id'])
        if can_collect:
            message += "✅ می‌توانید منابع روزانه را جمع‌آوری کنید."
        else:
            message += "⏳ هنوز نمی‌توانید منابع جمع‌آوری کنید (۲۴ ساعت نگذشته)."
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=Keyboards.get_resource_management()
        )
    
    # جمع‌آوری منابع
    elif data == "collect_resources":
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            await query.edit_message_text(
                "⚠️ شما کشوری ندارید!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        result = game_logic.collect_resources(player_country['id'])
        
        if result['success']:
            resources = result['resources']
            message = (
                f"✅ **منابع با موفقیت جمع‌آوری شد!**\n\n"
                f"🎁 **دریافتی‌های شما:**\n"
                f"   💰 طلا: +{resources['gold']}\n"
                f"   ⚒️ آهن: +{resources['iron']}\n"
                f"   🪨 سنگ: +{resources['stone']}\n"
                f"   🍖 غذا: +{resources['food']}\n\n"
                f"🔄 دفعه بعدی: ۲۴ ساعت دیگر"
            )
        else:
            message = f"❌ {result['message']}"
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=Keyboards.get_resource_management()
        )
    
    # آموزش ارتش
    elif data == "train_army":
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            await query.edit_message_text(
                "⚠️ شما کشوری ندارید!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        result = game_logic.train_army(player_country['id'])
        
        if result['success']:
            cost = result['cost']
            message = (
                f"✅ **آموزش سربازان با موفقیت انجام شد!**\n\n"
                f"🎖️ **نتیجه:**\n"
                f"   ⚔️ ۱۰ سرباز جدید آموزش دیدند\n\n"
                f"💸 **هزینه پرداخت شده:**\n"
                f"   💰 طلا: -{cost['gold']}\n"
                f"   ⚒️ آهن: -{cost['iron']}"
            )
        else:
            message = f"❌ {result['message']}"
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=Keyboards.get_resource_management()
        )
    
    # تقویت دفاع
    elif data == "upgrade_defense":
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            await query.edit_message_text(
                "⚠️ شما کشوری ندارید!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        result = game_logic.upgrade_defense(player_country['id'])
        
        if result['success']:
            cost = result['cost']
            message = (
                f"✅ **تقویت دفاع با موفقیت انجام شد!**\n\n"
                f"🛡️ **نتیجه:**\n"
                f"   دفاع کشور ۵ واحد تقویت شد\n\n"
                f"💸 **هزینه پرداخت شده:**\n"
                f"   💰 طلا: -{cost['gold']}\n"
                f"   🪨 سنگ: -{cost['stone']}"
            )
        else:
            message = f"❌ {result['message']}"
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=Keyboards.get_resource_management()
        )
    
    # اضافه کردن بازیکن (فقط مالک)
    elif data == "add_player":
        if user_id != config.OWNER_ID:
            await query.edit_message_text(
                "⛔ **دسترسی ممنوع!**\n\n"
                "فقط مالک بازی می‌تواند بازیکن اضافه کند.\n"
                f"👑 مالک: {config.OWNER_USERNAME}",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        # نمایش کشورهای آزاد
        available_countries = db.get_available_countries()
        
        if not available_countries:
            await query.edit_message_text(
                "⚠️ **همه کشورها اشغال شده‌اند!**\n\n"
                "در حال حاضر تمام ۱۲ کشور توسط بازیکنان یا AI اشغال شده‌اند.\n"
                "برای اضافه کردن بازیکن جدید باید یک کشور آزاد شود.",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        countries_list = [(c['id'], c['name'], c['special_resource'], c['color']) for c in available_countries]
        
        await query.edit_message_text(
            "🤴 **افزودن بازیکن جدید**\n\n"
            "🏛️ لطفاً کشوری را برای بازیکن جدید انتخاب کنید:\n\n"
            "هر کشور فقط می‌تواند یک بازیکن داشته باشد.",
            reply_markup=Keyboards.get_countries_keyboard(
                available_only=True, 
                countries_list=countries_list
            )
        )
    
    # انتخاب کشور برای بازیکن جدید
    elif data.startswith("country_"):
        if user_id != config.OWNER_ID:
            return
        
        country_id = int(data.split("_")[1])
        
        # ذخیره country_id در context برای مرحله بعد
        context.user_data['selected_country'] = country_id
        context.user_data['add_player_mode'] = True
        
        await query.edit_message_text(
            f"🏛️ کشور انتخاب شده: #{country_id}\n\n"
            f"📝 لطفاً **ایدی عددی** کاربر جدید را وارد کنید:\n\n"
            "⚠️ توجه: ایدی باید عددی باشد (نه @username)\n"
            "برای گرفتن ایدی عددی به @userinfobot مراجعه کنید.",
            reply_markup=Keyboards.get_cancel_keyboard()
        )
        
        return ENTERING_USER_ID
    
    # شروع فصل جدید (فقط مالک)
    elif data == "start_season":
        if user_id != config.OWNER_ID:
            await query.edit_message_text(
                "⛔ فقط مالک بازی می‌تواند فصل جدید شروع کند!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        # بررسی فصل فعال
        active_season = db.get_active_season()
        
        if active_season:
            await query.edit_message_text(
                f"⚠️ **فصل #{active_season['season_number']} در حال اجراست!**\n\n"
                f"ابتدا باید فصل فعلی را به پایان برسانید.",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        # شروع فصل جدید
        last_season = db.get_active_season()
        new_season_number = (last_season['season_number'] if last_season else 0) + 1
        
        season_id = db.start_season(new_season_number)
        
        if season_id:
            # ارسال پیام به کانال اگر تنظیم شده
            if config.CHANNEL_ID:
                try:
                    await context.bot.send_message(
                        chat_id=config.CHANNEL_ID,
                        text=f"🎉 **شروع فصل #{new_season_number} جنگ‌های باستان!**\n\n"
                             f"جهان باستان دوباره زنده شد!\n"
                             f"کشورها برای فتح جهان آماده می‌شوند...\n\n"
                             f"ساخته شده توسط {config.OWNER_USERNAME}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send message to channel: {e}")
            
            await query.edit_message_text(
                f"✅ **فصل #{new_season_number} با موفقیت شروع شد!**\n\n"
                f"📅 شماره فصل: #{new_season_number}\n"
                f"🆔 شناسه فصل: {season_id}\n"
                f"⏰ زمان شروع: اکنون\n\n"
                f"بازیکنان می‌توانند شروع به رقابت کنند!",
                reply_markup=Keyboards.get_main_menu(config.OWNER_ID, user_id)
            )
        else:
            await query.edit_message_text(
                "❌ خطا در شروع فصل جدید!",
                reply_markup=Keyboards.get_back_keyboard()
            )
    
    # پایان فصل (فقط مالک)
    elif data == "end_season":
        if user_id != config.OWNER_ID:
            await query.edit_message_text(
                "⛔ فقط مالک بازی می‌تواند فصل را پایان دهد!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        active_season = db.get_active_season()
        
        if not active_season:
            await query.edit_message_text(
                "⚠️ هیچ فصل فعالی وجود ندارد!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        # بررسی برنده
        winner_info = game_logic.check_season_winner(active_season['id'])
        
        if not winner_info:
            await query.edit_message_text(
                "⚠️ هیچ بازیکن انسانی برای برنده شدن وجود ندارد!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        # پایان فصل
        success = db.end_season(
            active_season['id'],
            winner_info['country_id'],
            winner_info['player_id']
        )
        
        if success:
            # ارسال پیام به کانال
            if config.CHANNEL_ID:
                try:
                    await context.bot.send_message(
                        chat_id=config.CHANNEL_ID,
                        text=f"🏆 **پایان فصل #{active_season['season_number']} جنگ‌های باستان**\n\n"
                             f"👑 **فاتح نهایی جهان:**\n"
                             f"🏛️ **{winner_info['country_name']}**\n"
                             f"👤 بازیکن: {winner_info['player_username']}\n"
                             f"📊 امتیاز: {winner_info['score']}\n"
                             f"⚡ قدرت کل: {winner_info['total_power']:.2f}\n\n"
                             f"ساخته شده توسط {config.OWNER_USERNAME}\n"
                             f"منتظر فصل بعد باشید!"
                    )
                except Exception as e:
                    logger.error(f"Failed to send message to channel: {e}")
            
            await query.edit_message_text(
                f"✅ **فصل #{active_season['season_number']} با موفقیت پایان یافت!**\n\n"
                f"🏆 **برنده فصل:**\n"
                f"   🏛️ کشور: {winner_info['country_name']}\n"
                f"   👤 بازیکن: {winner_info['player_username']}\n"
                f"   📊 امتیاز: {winner_info['score']}\n"
                f"   ⚡ قدرت کل: {winner_info['total_power']:.2f}\n\n"
                f"🎉 تبریک به فاتح جهان باستان!",
                reply_markup=Keyboards.get_main_menu(config.OWNER_ID, user_id)
            )
        else:
            await query.edit_message_text(
                "❌ خطا در پایان دادن به فصل!",
                reply_markup=Keyboards.get_back_keyboard()
            )
    
    # ریست بازی (فقط مالک)
    elif data == "reset_game":
        if user_id != config.OWNER_ID:
            await query.edit_message_text(
                "⛔ فقط مالک بازی می‌تواند بازی را ریست کند!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        await query.edit_message_text(
            "⚠️ **هشدار: ریست کامل بازی**\n\n"
            "آیا مطمئن هستید که می‌خواهید کل بازی را ریست کنید؟\n\n"
            "❌ **این عمل غیرقابل بازگشت است و:**\n"
            "• همه بازیکنان حذف می‌شوند\n"
            "• همه کشورها به حالت اولیه بازمی‌گردند\n"
            "• همه فصل‌ها و جنگ‌ها پاک می‌شوند\n"
            "• همه منابع و امتیازات ریست می‌شوند\n\n"
            "فقط در صورت نیاز واقعی این کار را انجام دهید!",
            reply_markup=Keyboards.get_confirmation_keyboard("reset")
        )
    
    # تأیید ریست
    elif data == "confirm_reset":
        if user_id != config.OWNER_ID:
            return
        
        # ریست بازی
        success = db.reset_game()
        
        if success:
            await query.edit_message_text(
                "✅ **بازی با موفقیت ریست شد!**\n\n"
                "🔄 همه داده‌ها به حالت اولیه بازگشتند:\n"
                "• بازیکنان حذف شدند\n"
                "• کشورها ریست شدند\n"
                "• فصل‌ها پاک شدند\n"
                "• جنگ‌ها حذف شدند\n\n"
                "اکنون می‌توانید بازی را از نو شروع کنید.",
                reply_markup=Keyboards.get_main_menu(config.OWNER_ID, user_id)
            )
        else:
            await query.edit_message_text(
                "❌ خطا در ریست کردن بازی!",
                reply_markup=Keyboards.get_back_keyboard()
            )
    
    # لغو عملیات
    elif data == "cancel_action":
        await query.edit_message_text(
            "❌ عملیات لغو شد.",
            reply_markup=Keyboards.get_main_menu(config.OWNER_ID, user_id)
        )
    
    # رتبه‌بندی
    elif data == "leaderboard":
        top_players = db.get_top_players(limit=10)
        
        if not top_players:
            await query.edit_message_text(
                "📊 هنوز هیچ بازیکنی در سیستم ثبت نشده است!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        message = "🏆 **رتبه‌بندی برترین بازیکنان:**\n\n"
        
        for i, player in enumerate(top_players, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
            
            message += (
                f"{medal} **{player['username']}**\n"
                f"   🏛️ کشور: {player['country_name']}\n"
                f"   📊 امتیاز: {player['score']}\n"
                f"   ⚡ قدرت: {player['total_power']:.2f}\n"
                f"   {'─' * 20}\n"
            )
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=Keyboards.get_back_keyboard()
        )
    
    # حمله به کشور
    elif data == "attack_country":
        player_country = db.get_player_country(user_id)
        
        if not player_country:
            await query.edit_message_text(
                "⚠️ شما کشوری ندارید!",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        # بررسی فصل فعال
        active_season = db.get_active_season()
        if not active_season:
            await query.edit_message_text(
                "⚠️ **هیچ فصل فعالی وجود ندارد!**\n\n"
                "برای حمله باید فصل بازی فعال باشد.\n"
                "لطفاً منتظر شروع فصل جدید بمانید.",
                reply_markup=Keyboards.get_back_keyboard()
            )
            return
        
        # نمایش کشورهای قابل حمله
        await query.edit_message_text(
            f"⚔️ **انتخاب هدف برای حمله**\n\n"
            f"🏛️ کشور شما: {player_country['name']}\n"
            f"⚔️ قدرت ارتش: {player_country['army']}\n"
            f"🛡️ قدرت دفاع: {player_country['defense']}\n\n"
            f"لطفاً کشوری را برای حمله انتخاب کنید:",
            reply_markup=Keyboards.get_attack_targets_keyboard(player_country['id'])
        )
    
    # حمله به کشور خاص
    elif data.startswith("attack_"):
        try:
            defender_id = int(data.split("_")[1])
            player_country = db.get_player_country(user_id)
            
            if not player_country:
                await query.edit_message_text(
                    "⚠️ شما کشوری ندارید!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # بررسی فصل فعال
            active_season = db.get_active_season()
            if not active_season:
                await query.edit_message_text(
                    "⚠️ هیچ فصل فعالی وجود ندارد!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # حمله به خود ممنوع
            if defender_id == player_country['id']:
                await query.edit_message_text(
                    "❌ نمی‌توانید به کشور خود حمله کنید!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # شبیه‌سازی حمله
            result = game_logic.attack_country(
                player_country['id'],
                defender_id,
                active_season['id']
            )
            
            if result['success']:
                battle_result = result['result']
                
                if battle_result['result'].startswith('attacker'):
                    # حمله‌کننده برنده شد
                    message = (
                        f"🎉 **پیروزی در نبرد!**\n\n"
                        f"⚔️ **نتیجه نبرد:**\n"
                        f"   🏛️ حمله‌کننده: {player_country['name']}\n"
                        f"   🎯 مدافع: #{defender_id}\n"
                        f"   📊 نسبت قدرت: {battle_result['power_ratio']}\n\n"
                        f"💀 **تلفات:**\n"
                        f"   ⚔️ تلفات شما: {battle_result['attacker_losses']} سرباز\n"
                        f"   🛡️ تلفات دشمن: {battle_result['defender_losses']} سرباز\n\n"
                        f"🎁 **غنائم کسب شده:**\n"
                        f"   💰 طلا: +{battle_result['loot']['gold']}\n"
                        f"   ⚒️ آهن: +{battle_result['loot']['iron']}\n"
                        f"   🪨 سنگ: +{battle_result['loot']['stone']}\n"
                        f"   🍖 غذا: +{battle_result['loot']['food']}\n\n"
                        f"✅ امتیاز شما افزایش یافت!"
                    )
                else:
                    # مدافع برنده شد یا تساوی
                    result_text = "تساوی" if battle_result['result'] == 'draw' else "شکست"
                    message = (
                        f"😔 **{result_text} در نبرد**\n\n"
                        f"⚔️ **نتیجه نبرد:**\n"
                        f"   🏛️ حمله‌کننده: {player_country['name']}\n"
                        f"   🎯 مدافع: #{defender_id}\n"
                        f"   📊 نسبت قدرت: {battle_result['power_ratio']}\n\n"
                        f"💀 **تلفات:**\n"
                        f"   ⚔️ تلفات شما: {battle_result['attacker_losses']} سرباز\n"
                        f"   🛡️ تلفات دشمن: {battle_result['defender_losses']} سرباز\n\n"
                        f"📉 قدرت ارتش شما کاهش یافت."
                    )
                
                await query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=Keyboards.get_back_keyboard()
                )
            else:
                await query.edit_message_text(
                    f"❌ {result['message']}",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                
        except ValueError:
            await query.edit_message_text(
                "❌ خطا در پردازش حمله!",
                reply_markup=Keyboards.get_back_keyboard()
            )
    
    # راهنما
    elif data == "help":
        await help_command(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # بررسی اگر مالک در حال اضافه کردن بازیکن است
    if user_id == config.OWNER_ID and context.user_data.get('add_player_mode'):
        try:
            new_user_id = int(text)
            country_id = context.user_data.get('selected_country')
            
            if not country_id:
                await update.message.reply_text(
                    "❌ خطا: کشور انتخاب نشده است!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # اضافه کردن بازیکن
            result = db.add_player(
                new_user_id,
                update.effective_user.username or f"player_{new_user_id}",
                country_id
            )
            
            if result['success']:
                # اطلاع به بازیکن جدید
                try:
                    await context.bot.send_message(
                        chat_id=new_user_id,
                        text=f"🎉 **به بازی جنگ جهانی باستان خوش آمدید!**\n\n"
                             f"🏛️ کشور شما: #{country_id}\n"
                             f"👑 مالک بازی: {config.OWNER_USERNAME}\n\n"
                             f"برای شروع بازی از دستور /start استفاده کنید.\n"
                             f"برای راهنمای بازی از /help استفاده کنید.",
                        reply_markup=Keyboards.get_main_menu(config.OWNER_ID, new_user_id)
                    )
                except Exception as e:
                    logger.error(f"Failed to notify new player: {e}")
                
                await update.message.reply_text(
                    f"✅ **بازیکن با موفقیت اضافه شد!**\n\n"
                    f"👤 آیدی بازیکن: {new_user_id}\n"
                    f"🏛️ کشور اختصاص یافته: #{country_id}\n\n"
                    f"پیام خوش‌آمد به بازیکن ارسال شد.",
                    reply_markup=Keyboards.get_main_menu(config.OWNER_ID, user_id)
                )
            else:
                await update.message.reply_text(
                    f"❌ {result['message']}",
                    reply_markup=Keyboards.get_main_menu(config.OWNER_ID, user_id)
                )
            
            # پاک کردن وضعیت
            context.user_data.clear()
            
        except ValueError:
            await update.message.reply_text(
                "⚠️ لطفاً یک **ایدی عددی** معتبر وارد کنید!\n\n"
                "برای گرفتن ایدی عددی:\n"
                "1. به @userinfobot بروید\n"
                "2. دستور /start را بزنید\n"
                "3. ایدی عددی را کپی کنید",
                reply_markup=Keyboards.get_cancel_keyboard()
            )
        except Exception as e:
            logger.error(f"Error in handle_text: {e}")
            await update.message.reply_text(
                "❌ خطای سیستمی!",
                reply_markup=Keyboards.get_main_menu(config.OWNER_ID, user_id)
            )
    else:
        # پیام معمولی
        await update.message.reply_text(
            "لطفاً از دکمه‌های موجود در منو استفاده کنید.",
            reply_markup=Keyboards.get_main_menu(config.OWNER_ID, user_id)
        )

@flask_app.route('/webhook', methods=['POST'])
async def webhook():
    """Webhook endpoint برای Render"""
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json_str, bot)
    
    # Process the update
    await application.process_update(update)
    return 'OK'

@flask_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'ancient-war-bot'}

def create_app():
    """ایجاد برنامه"""
    global application, bot
    
    # ایجاد برنامه Telegram
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # ایجاد ConversationHandler برای افزودن بازیکن
    add_player_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^add_player$')],
        states={
            SELECTING_COUNTRY: [
                CallbackQueryHandler(button_handler, pattern='^country_')
            ],
            ENTERING_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u,c: ConversationHandler.END),
            CallbackQueryHandler(button_handler, pattern='^main_menu$')
        ],
        map_to_parent={
            ConversationHandler.END: SELECTING_COUNTRY
        }
    )
    
    # اضافه کردن handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(add_player_conv)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    bot = Bot(token=config.BOT_TOKEN)
    
    return application

def run_polling():
    """اجرای با Polling"""
    app = create_app()
    logger.info("🤖 Starting bot with polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

def run_webhook():
    """اجرای با Webhook برای Render"""
    global application, bot
    
    app = create_app()
    
    # تنظیم webhook اگر URL داده شده
    if config.WEBHOOK_URL:
        webhook_url = f"{config.WEBHOOK_URL}/webhook"
        bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
    
    # اجرای Flask
    logger.info(f"🚀 Starting Flask on port {config.PORT}")
    flask_app.run(host='0.0.0.0', port=config.PORT)

if __name__ == '__main__':
    # بررسی محیط اجرا
    if os.getenv('RENDER') or config.WEBHOOK_URL:
        logger.info("🚀 Running in Render/Webhook environment")
        run_webhook()
    else:
        logger.info("💻 Running in local environment (Polling mode)")
        run_polling()
