import os
import logging
from datetime import datetime
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError
from config import BOT_TOKEN, OWNER_ID, CHANNEL_ID, DATABASE_PATH
from database import Database
from game_logic import GameLogic
from keyboards import Keyboards

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ایجاد نمونه‌های دیتابیس و منطق بازی
db = Database()
game_logic = GameLogic(db)

# ایجاد برنامه Flask
app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات"""
    user = update.effective_user
    user_id = user.id
    
    welcome_message = (
        f"👋 سلام {user.first_name}!\n"
        f"به بازی جنگ جهانی باستان خوش آمدید.\n\n"
        f"شما در حال حاضر: {'👑 مالک بازی' if user_id == OWNER_ID else '🎮 بازیکن'}\n"
        f"برای ادامه از دکمه‌های زیر استفاده کنید:"
    )
    
    if update.message:
        await update.message.reply_text(
            welcome_message,
            reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            welcome_message,
            reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنما"""
    help_text = (
        "📚 **راهنمای ربات جنگ جهانی باستان**\n\n"
        "👑 **مالک بازی:**\n"
        "• افزودن بازیکن جدید\n"
        "• شروع و پایان فصل\n"
        "• مشاهده تمام کشورها\n"
        "• ریست کامل بازی\n\n"
        "🎮 **بازیکنان:**\n"
        "• مشاهده کشور خود\n"
        "• مدیریت منابع\n"
        "• مشاهده وضعیت کلی\n\n"
        "📝 **دستورات:**\n"
        "/start - شروع ربات\n"
        "/help - نمایش این راهنما\n"
        "/status - وضعیت بازی\n\n"
        "📞 پشتیبانی: @amele55"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور وضعیت بازی"""
    user_id = update.effective_user.id
    
    # دریافت اطلاعات بازی
    active_season = db.get_active_season()
    countries = db.get_all_countries()
    available_countries = db.get_available_countries()
    
    # محاسبه آمار
    total_countries = len(countries)
    human_countries = len([c for c in countries if c[4] == 'HUMAN'])
    ai_countries = total_countries - human_countries
    
    status_message = (
        f"📊 **وضعیت فعلی بازی**\n\n"
        f"🌍 **کشورها:**\n"
        f"• کل کشورها: {total_countries}\n"
        f"• بازیکنان انسانی: {human_countries}\n"
        f"• کشورهای هوش مصنوعی: {ai_countries}\n"
        f"• کشورهای آزاد: {len(available_countries)}\n\n"
    )
    
    if active_season:
        season_number = active_season[1]
        start_date = active_season[2]
        status_message += (
            f"📅 **فصل فعال:**\n"
            f"• شماره فصل: #{season_number}\n"
            f"• تاریخ شروع: {start_date}\n"
            f"• وضعیت: 🟢 فعال\n\n"
        )
    else:
        status_message += "📅 **فصل فعال:** ❌ هیچ فصل فعالی وجود ندارد\n\n"
    
    # وضعیت کاربر
    player_country = db.get_player_country(user_id)
    if player_country:
        status_message += f"🏛️ **کشور شما:** {player_country[1]}\n"
    elif user_id == OWNER_ID:
        status_message += "👑 **نقش شما:** مالک بازی\n"
    else:
        status_message += "⚠️ **توجه:** شما هنوز کشوری ندارید. از مالک بخواهید برای شما کشور اختصاص دهد.\n"
    
    await update.message.reply_text(status_message, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    logger.info(f"Button clicked by {user_id}: {data}")
    
    try:
        if data == "main_menu":
            await start(update, context)
        
        elif data == "add_player":
            if user_id != OWNER_ID:
                await query.edit_message_text(
                    "⛔ دسترسی ممنوع!\nفقط مالک بازی می‌تواند بازیکن اضافه کند.",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # نمایش کشورهای آزاد
            available_countries = db.get_available_countries()
            
            if not available_countries:
                await query.edit_message_text(
                    "⚠️ همه کشورها در حال حاضر توسط بازیکنان اشغال شده‌اند!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            countries_list = [(c[1], c[0]) for c in available_countries]
            
            await query.edit_message_text(
                "🏛️ انتخاب کشور برای بازیکن جدید:\n\n"
                "لطفاً یکی از کشورهای زیر را انتخاب کنید:",
                reply_markup=Keyboards.get_countries_keyboard(
                    available_only=True, 
                    countries_list=countries_list
                )
            )
        
        elif data.startswith("country_"):
            if user_id != OWNER_ID:
                await query.edit_message_text(
                    "⛔ دسترسی ممنوع!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            country_id = int(data.split("_")[1])
            
            # دریافت نام کشور
            country = db.get_country_by_id(country_id)
            if not country:
                await query.edit_message_text(
                    "❌ کشور مورد نظر یافت نشد!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # ذخیره country_id در context برای مرحله بعد
            context.user_data['selected_country'] = country_id
            context.user_data['selected_country_name'] = country[1]
            
            await query.edit_message_text(
                f"🏛️ کشور انتخاب شده: **{country[1]}**\n\n"
                f"لطفاً آیدی عددی کاربر را وارد کنید:\n"
                f"(آیدی را به صورت عددی بفرستید)",
                parse_mode='Markdown',
                reply_markup=Keyboards.get_back_keyboard()
            )
        
        elif data == "view_countries":
            countries = db.get_all_countries()
            
            if not countries:
                await query.edit_message_text(
                    "⚠️ هیچ کشوری در دیتابیس وجود ندارد!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            message = "🌍 **فهرست کشورهای جهان باستان:**\n\n"
            
            for country in countries[:15]:  # محدود کردن به 15 کشور برای جلوگیری از طولانی شدن
                country_id, name, special, color, controller, player_id = country[:6]
                gold, iron, stone, food, army, defense = country[6:12]
                
                controller_name = "🤖 AI" if controller == 'AI' else f"👤 {player_id}"
                status_emoji = "🟢" if controller == 'AI' else "🔴"
                
                message += (
                    f"{status_emoji} **{name}**\n"
                    f"   📍 شناسه: #{country_id}\n"
                    f"   🎁 منبع ویژه: {special}\n"
                    f"   👤 کنترل‌کننده: {controller_name}\n"
                    f"   ⚔️ ارتش: {army} | 🛡️ دفاع: {defense}\n"
                    f"   💰 طلا: {gold} | ⚒️ آهن: {iron}\n"
                    f"   🪨 سنگ: {stone} | 🍖 غذا: {food}\n"
                    f"   {'─'*30}\n"
                )
            
            if len(countries) > 15:
                message += f"\n... و {len(countries) - 15} کشور دیگر"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=Keyboards.get_back_keyboard()
            )
        
        elif data == "my_country":
            # مشاهده کشور بازیکن
            player_country = db.get_player_country(user_id)
            
            if not player_country:
                await query.edit_message_text(
                    "⚠️ شما هنوز کشوری ندارید!\n"
                    "لطفاً از مالک بازی درخواست کشور کنید.",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            country_id, name, special, color, controller = player_country[:5]
            gold, iron, stone, food, army, defense = player_country[6:12]
            
            message = (
                f"🏛️ **کشور شما: {name}**\n"
                f"📍 شناسه: #{country_id}\n\n"
                f"🎁 منبع ویژه: **{special}**\n"
                f"🎨 رنگ پرچم: `{color}`\n\n"
                f"**📦 منابع:**\n"
                f"💰 طلا: `{gold}`\n"
                f"⚒️ آهن: `{iron}`\n"
                f"🪨 سنگ: `{stone}`\n"
                f"🍖 غذا: `{food}`\n\n"
                f"**⚔️ نظامی:**\n"
                f"👥 ارتش: `{army}` نفر\n"
                f"🛡️ دفاع: `{defense}`%\n\n"
                f"برای مدیریت از دکمه‌های زیر استفاده کنید:"
            )
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=Keyboards.get_resource_management()
            )
        
        elif data == "view_resources":
            player_country = db.get_player_country(user_id)
            
            if not player_country:
                await query.edit_message_text(
                    "⚠️ شما کشوری ندارید!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            country_id, name, special = player_country[:3]
            gold, iron, stone, food, army = player_country[6:11]
            
            # محاسبه منابع روزانه
            daily = game_logic.calculate_daily_resources(country_id)
            
            message = (
                f"📊 **وضعیت منابع {name}**\n"
                f"📍 شناسه: #{country_id}\n\n"
                f"🎁 منبع ویژه: **{special}**\n\n"
                f"**📦 موجودی فعلی:**\n"
                f"💰 طلا: `{gold}`\n"
                f"⚒️ آهن: `{iron}`\n"
                f"🪨 سنگ: `{stone}`\n"
                f"🍖 غذا: `{food}`\n"
                f"👥 ارتش: `{army}` نفر\n\n"
            )
            
            if daily:
                food_cost = army * 0.1
                daily_food = max(0, daily['food'] - food_cost)
                
                message += (
                    f"**📈 تولید روزانه:**\n"
                    f"💰 طلا: `+{daily['gold']}`\n"
                    f"⚒️ آهن: `+{daily['iron']}`\n"
                    f"🪨 سنگ: `+{daily['stone']}`\n"
                    f"🍖 غذا: `+{daily['food']}`\n"
                    f"   (هزینه ارتش: `-{food_cost:.1f}` = `{daily_food:.1f}` خالص)\n\n"
                )
            
            message += "برای مدیریت منابع از منوی اصلی استفاده کنید."
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=Keyboards.get_back_keyboard()
            )
        
        elif data == "start_season":
            if user_id != OWNER_ID:
                await query.edit_message_text(
                    "⛔ فقط مالک بازی می‌تواند فصل جدید شروع کند!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # بررسی فصل فعال
            active_season = db.get_active_season()
            
            if active_season:
                await query.edit_message_text(
                    f"⚠️ فصل #{active_season[1]} در حال اجراست!\n"
                    f"تاریخ شروع: {active_season[2]}\n"
                    f"ابتدا فصل فعلی را به پایان برسانید.",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # شروع فصل جدید
            seasons_history = db.get_season_history()
            new_season_number = 1
            
            if seasons_history:
                new_season_number = seasons_history[0][1] + 1
            
            season_id = db.start_season(new_season_number)
            
            # ارسال پیام به کانال
            try:
                bot = context.bot
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=(
                        f"🎉 **شروع فصل #{new_season_number} جنگ‌های باستان!**\n\n"
                        f"جهان باستان زنده شد! کشورها برای فتح جهان آماده می‌شوند...\n\n"
                        f"برای پیوستن به بازی با @{context.bot.username} ارتباط برقرار کنید.\n"
                        f"ساخته شده توسط @amele55\n"
                        f"✈️ ورژن 1.0 ربات"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send message to channel: {e}")
            
            await query.edit_message_text(
                f"✅ فصل #{new_season_number} با موفقیت شروع شد!\n\n"
                f"🆔 شناسه فصل: `{season_id}`\n"
                f"📅 تاریخ شروع: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"📢 پیام شروع فصل در کانال ارسال شد.",
                parse_mode='Markdown',
                reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
            )
        
        elif data == "end_season":
            if user_id != OWNER_ID:
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
            winner_info = game_logic.check_season_winner(active_season[0])
            
            if not winner_info:
                await query.edit_message_text(
                    "⚠️ هیچ بازیکن انسانی برای برنده شدن وجود ندارد!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            # پایان فصل
            db.end_season(
                active_season[0],
                winner_info['country_id'],
                winner_info['player_id']
            )
            
            # دریافت اطلاعات برنده
            winner_country = db.get_country_by_id(winner_info['country_id'])
            
            # ارسال پیام به کانال
            try:
                bot = context.bot
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=(
                        f"🏆 **پایان فصل #{active_season[1]} جنگ‌های باستان**\n\n"
                        f"👑 فاتح نهایی جهان:\n"
                        f"🏛️ **{winner_country[1]}**\n"
                        f"👤 بازیکن: {winner_info['player_id']}\n"
                        f"📊 امتیاز نهایی: `{winner_info['score']:.2f}`\n\n"
                        f"برای پیوستن به فصل بعد با @{context.bot.username} ارتباط برقرار کنید.\n"
                        f"ساخته شده توسط @amele55\n"
                        f"✈️ ورژن 1.0 ربات"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send message to channel: {e}")
            
            await query.edit_message_text(
                f"✅ فصل #{active_season[1]} با موفقیت پایان یافت!\n\n"
                f"🏆 **برنده فصل:**\n"
                f"🏛️ کشور: {winner_country[1]}\n"
                f"👤 بازیکن: `{winner_info['player_id']}`\n"
                f"📊 امتیاز: `{winner_info['score']:.2f}`\n\n"
                f"📅 مدت فصل: از {active_season[2]} تا {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                parse_mode='Markdown',
                reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
            )
        
        elif data == "reset_game":
            if user_id != OWNER_ID:
                await query.edit_message_text(
                    "⛔ فقط مالک بازی می‌تواند بازی را ریست کند!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
                return
            
            await query.edit_message_text(
                "⚠️ **هشدار: ریست کامل بازی**\n\n"
                "❌ **این عمل غیرقابل بازگشت است!**\n\n"
                "📋 **مواردی که پاک می‌شوند:**\n"
                "• همه بازیکنان\n"
                "• همه فصل‌های فعال\n"
                "• همه رویدادها\n"
                "• همه کشورها به حالت اولیه بازمی‌گردند\n\n"
                "آیا مطمئن هستید؟",
                parse_mode='Markdown',
                reply_markup=Keyboards.get_confirmation_keyboard("reset")
            )
        
        elif data == "confirm_reset":
            if user_id != OWNER_ID:
                return
            
            # ریست بازی
            success = db.reset_game()
            
            if success:
                await query.edit_message_text(
                    "✅ **بازی با موفقیت ریست شد!**\n\n"
                    "📋 **نتایج ریست:**\n"
                    "✔️ همه کشورها به حالت اولیه بازگشتند\n"
                    "✔️ فصل‌های فعال به پایان رسیدند\n"
                    "✔️ بازیکنان حذف شدند\n"
                    "✔️ رویدادها پاک شدند\n\n"
                    "🏛️ بازی آماده شروع جدید است.",
                    parse_mode='Markdown',
                    reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
                )
            else:
                await query.edit_message_text(
                    "❌ خطا در ریست بازی!",
                    reply_markup=Keyboards.get_back_keyboard()
                )
        
        elif data == "cancel_action":
            await query.edit_message_text(
                "❌ عملیات لغو شد.",
                reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
            )
        
        elif data in ["army_management", "diplomacy"]:
            await query.edit_message_text(
                f"⚙️ **قابلیت در حال توسعه**\n\n"
                f"ویژگی '{data}' در نسخه‌های آینده اضافه خواهد شد.\n"
                f"لطفاً در نسخه‌های بعدی بررسی کنید.",
                reply_markup=Keyboards.get_back_keyboard()
            )
        
        elif data.startswith("resource_"):
            resource_type = data.split("_")[1]
            resource_names = {
                'gold': '💰 طلا',
                'iron': '⚒️ آهن',
                'stone': '🪨 سنگ',
                'food': '🍖 غذا'
            }
            
            resource_name = resource_names.get(resource_type, resource_type)
            
            await query.edit_message_text(
                f"📊 **مدیریت {resource_name}**\n\n"
                f"این بخش در نسخه بعدی برای مدیریت منابع اضافه خواهد شد.\n\n"
                f"در حال حاضر می‌توانید وضعیت منابع خود را از منوی اصلی مشاهده کنید.",
                reply_markup=Keyboards.get_back_keyboard()
            )
        
        elif data in ["army_info", "defense_info"]:
            info_type = "ارتش" if data == "army_info" else "دفاع"
            
            await query.edit_message_text(
                f"🛡️ **اطلاعات {info_type}**\n\n"
                f"این بخش در نسخه بعدی کامل خواهد شد.\n\n"
                f"در حال حاضر می‌توانید از بخش 'مشاهده کشور من' اطلاعات نظامی خود را ببینید.",
                reply_markup=Keyboards.get_back_keyboard()
            )
        
        else:
            await query.edit_message_text(
                "⚠️ دستور نامعتبر!\nلطفاً از منوی اصلی استفاده کنید.",
                reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
            )
    
    except Exception as e:
        logger.error(f"Error in button handler: {e}")
        await query.edit_message_text(
            "❌ خطایی در پردازش درخواست شما رخ داد!\nلطفاً دوباره تلاش کنید.",
            reply_markup=Keyboards.get_back_keyboard()
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    try:
        # بررسی اگر مالک در حال اضافه کردن بازیکن است
        if user_id == OWNER_ID and 'selected_country' in context.user_data:
            try:
                new_user_id = int(text)
                country_id = context.user_data['selected_country']
                country_name = context.user_data.get('selected_country_name', f'#{country_id}')
                
                # اضافه کردن بازیکن
                success = db.add_player(
                    new_user_id,
                    f"player_{new_user_id}",
                    country_id
                )
                
                if success:
                    # اطلاع به مالک
                    await update.message.reply_text(
                        f"✅ **بازیکن با موفقیت اضافه شد!**\n\n"
                        f"👤 آیدی بازیکن: `{new_user_id}`\n"
                        f"🏛️ کشور اختصاص‌یافته: **{country_name}**\n"
                        f"📍 شناسه کشور: #{country_id}",
                        parse_mode='Markdown',
                        reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
                    )
                    
                    # اطلاع به بازیکن جدید
                    try:
                        country_info = db.get_country_by_id(country_id)
                        await context.bot.send_message(
                            chat_id=new_user_id,
                            text=(
                                f"🎉 **شما به بازی جنگ جهانی باستان اضافه شدید!**\n\n"
                                f"🏛️ کشور شما: **{country_info[1]}**\n"
                                f"📍 شناسه: #{country_id}\n"
                                f"🎁 منبع ویژه: {country_info[2]}\n"
                                f"🎨 رنگ پرچم: {country_info[3]}\n\n"
                                f"برای شروع بازی دستور /start را ارسال کنید.\n"
                                f"موفق باشید! 🏆"
                            ),
                            parse_mode='Markdown',
                            reply_markup=Keyboards.get_main_menu(OWNER_ID, new_user_id)
                        )
                    except TelegramError as e:
                        logger.error(f"Failed to notify new player {new_user_id}: {e}")
                        await update.message.reply_text(
                            f"⚠️ **هشدار:**\n"
                            f"بازیکن اضافه شد اما نتوانستم به او پیام بدهم.\n"
                            f"لطفاً به کاربر `{new_user_id}` اطلاع دهید که از ربات استفاده کند.",
                            reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
                        )
                        
                else:
                    await update.message.reply_text(
                        "❌ **خطا در اضافه کردن بازیکن!**\n\n"
                        "دلایل احتمالی:\n"
                        "• کشور قبلاً اشغال شده است\n"
                        "• کشور در دیتابیس وجود ندارد\n"
                        "• خطای دیتابیس",
                        reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
                    )
                
                # پاک کردن وضعیت
                context.user_data.pop('selected_country', None)
                context.user_data.pop('selected_country_name', None)
                
            except ValueError:
                await update.message.reply_text(
                    "⚠️ **ورودی نامعتبر!**\n\n"
                    "لطفاً یک **آیدی عددی معتبر** وارد کنید.\n"
                    "مثال: `123456789`",
                    parse_mode='Markdown',
                    reply_markup=Keyboards.get_back_keyboard()
                )
        else:
            await update.message.reply_text(
                "👋 برای استفاده از ربات:\n\n"
                "1. از دکمه‌های منو استفاده کنید\n"
                "2. یا دستور /start را ارسال کنید\n\n"
                "در صورت مشکل با مالک بازی تماس بگیرید.",
                reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
            )
    
    except Exception as e:
        logger.error(f"Error in handle_text: {e}")
        await update.message.reply_text(
            "❌ خطایی در پردازش پیام شما رخ داد!",
            reply_markup=Keyboards.get_main_menu(OWNER_ID, user_id)
        )

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint برای Render"""
    try:
        json_str = request.get_data().decode('UTF-8')
        update = Update.de_json(json_str, application.bot)
        application.update_queue.put_nowait(update)
        return 'OK'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'ERROR', 400

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint برای Render"""
    try:
        # تست اتصال به دیتابیس
        countries_count = len(db.get_all_countries())
        active_season = db.get_active_season()
        
        return {
            'status': 'healthy',
            'service': 'ancient-war-bot',
            'version': '1.0',
            'database': {
                'countries_count': countries_count,
                'has_active_season': active_season is not None
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500

@app.route('/', methods=['GET'])
def index():
    """صفحه اصلی"""
    return '''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ancient War Bot - ربات جنگ جهانی باستان</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            body {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #fff;
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            
            header {
                text-align: center;
                margin-bottom: 40px;
                padding: 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            h1 {
                font-size: 3rem;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #fbbf24, #f59e0b);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
            }
            
            .tagline {
                font-size: 1.2rem;
                color: #cbd5e1;
                margin-bottom: 20px;
            }
            
            .status-badge {
                display: inline-block;
                padding: 8px 20px;
                background: linear-gradient(45deg, #10b981, #059669);
                border-radius: 20px;
                font-weight: bold;
                margin: 10px 0;
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            }
            
            .info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            
            .info-card {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                padding: 25px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: all 0.3s ease;
            }
            
            .info-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                border-color: #f59e0b;
            }
            
            .info-card h3 {
                color: #f59e0b;
                margin-bottom: 15px;
                font-size: 1.5rem;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .info-card p {
                color: #cbd5e1;
                line-height: 1.6;
            }
            
            .features {
                margin: 40px 0;
            }
            
            .features h2 {
                text-align: center;
                margin-bottom: 30px;
                color: #fbbf24;
                font-size: 2rem;
            }
            
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
            }
            
            .feature-item {
                background: rgba(255, 255, 255, 0.03);
                padding: 15px;
                border-radius: 10px;
                border-left: 4px solid #f59e0b;
            }
            
            .footer {
                text-align: center;
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                color: #94a3b8;
            }
            
            .btn {
                display: inline-block;
                padding: 12px 30px;
                background: linear-gradient(45deg, #f59e0b, #d97706);
                color: white;
                text-decoration: none;
                border-radius: 25px;
                font-weight: bold;
                margin: 10px;
                transition: all 0.3s ease;
                border: none;
                cursor: pointer;
            }
            
            .btn:hover {
                transform: scale(1.05);
                box-shadow: 0 5px 20px rgba(245, 158, 11, 0.4);
            }
            
            @media (max-width: 768px) {
                h1 {
                    font-size: 2rem;
                }
                
                .container {
                    padding: 10px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🤖 ربات جنگ جهانی باستان</h1>
                <p class="tagline">تجربه‌ای متفاوت از جنگ‌های تاریخی در تلگرام</p>
                <div class="status-badge">✅ سرویس فعال</div>
                <p>ربات مدیریت بازی استراتژیک چندنفره در محیط تلگرام</p>
            </header>
            
            <div class="info-grid">
                <div class="info-card">
                    <h3>🏛️ درباره بازی</h3>
                    <p>یک بازی استراتژیک چندنفره که در آن هر بازیکن کنترل یک تمدن باستانی را به دست می‌گیرد. منابع خود را مدیریت کنید، ارتش بسازید و جهان را فتح کنید!</p>
                </div>
                
                <div class="info-card">
                    <h3>👑 مالک بازی</h3>
                    <p>مالک می‌تواند بازیکنان جدید اضافه کند، فصل‌ها را مدیریت کند و بر کل بازی نظارت داشته باشد.</p>
                </div>
                
                <div class="info-card">
                    <h3>🎮 ویژگی‌ها</h3>
                    <p>• مدیریت منابع (طلا، آهن، سنگ، غذا)<br>
                       • سیستم ارتش و جنگ<br>
                       • دیپلماسی و اتحاد<br>
                       • فصل‌های رقابتی<br>
                       • هوش مصنوعی برای کشورهای خالی</p>
                </div>
            </div>
            
            <div class="features">
                <h2>🚀 ویژگی‌های کلیدی</h2>
                <div class="features-grid">
                    <div class="feature-item">🏛️ ۱۰ تمدن باستانی متفاوت</div>
                    <div class="feature-item">⚔️ سیستم نبرد واقعی</div>
                    <div class="feature-item">📊 مدیریت منابع پیشرفته</div>
                    <div class="feature-item">🏆 سیستم رقابت فصلی</div>
                    <div class="feature-item">🤖 هوش مصنوعی هوشمند</div>
                    <div class="feature-item">📱 رابط کاربری فارسی</div>
                </div>
            </div>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="/health" class="btn">بررسی وضعیت سرویس</a>
            </div>
            
            <div class="footer">
                <p>© 2024 Ancient War Bot - ساخته شده توسط @amele55</p>
                <p>ورژن 1.0 | آخرین به‌روزرسانی: بهمن ۱۴۰۳</p>
                <p style="margin-top: 20px; font-size: 0.9rem;">
                    این پروژه یک بازی استراتژیک چندنفره است که با Python و Telegram Bot API توسعه یافته است.
                </p>
            </div>
        </div>
    </body>
    </html>
    '''

def setup_handlers(application):
    """تنظیم handlers برای ربات"""
    # اضافه کردن handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

def create_application():
    """ایجاد برنامه Telegram"""
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    return application

# ایجاد برنامه Telegram
application = create_application()
