import os
import time
import logging
from datetime import datetime, timedelta
from app import execute_query, calculate_daily_production

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_daily_production():
    """پردازش تولید روزانه منابع"""
    logger.info("🔄 شروع پردازش تولید روزانه...")
    
    # گرفتن تمام بازیکنان
    players = execute_query('SELECT user_id FROM players WHERE country IS NOT NULL', fetchall=True)
    
    for player in players:
        user_id = player[0]
        production = calculate_daily_production(user_id)
        
        if production:
            execute_query('''
                UPDATE players 
                SET gold = gold + ?, 
                    iron = iron + ?, 
                    stone = stone + ?, 
                    food = food + ?,
                    wood = wood + ?,
                    last_active = ?
                WHERE user_id = ?
            ''', (
                production['gold'],
                production['iron'],
                production['stone'],
                production['food'],
                production['wood'],
                datetime.now(),
                user_id
            ), commit=True)
            
            logger.info(f"✅ منابع برای کاربر {user_id} اضافه شد")
    
    logger.info("✅ پردازش تولید روزانه تکمیل شد")

def cleanup_old_data():
    """پاک‌سازی داده‌های قدیمی"""
    logger.info("🧹 شروع پاک‌سازی داده‌های قدیمی...")
    
    # پاک‌سازی دیپلماسی منقضی شده
    execute_query('''
        DELETE FROM diplomacy 
        WHERE expires_at < ? OR (status = 'pending' AND created_at < ?)
    ''', (datetime.now(), datetime.now() - timedelta(days=7)), commit=True)
    
    logger.info("✅ پاک‌سازی داده‌های قدیمی تکمیل شد")

def main():
    """تابع اصلی Worker"""
    logger.info("👷 Worker Ancient War Bot شروع به کار کرد")
    
    while True:
        try:
            current_hour = datetime.now().hour
            
            # پردازش تولید روزانه در ساعت 00:00
            if current_hour == 0:
                process_daily_production()
            
            # پاک‌سازی روزانه در ساعت 03:00
            if current_hour == 3:
                cleanup_old_data()
            
            # استراحت 1 ساعت
            time.sleep(3600)
            
        except Exception as e:
            logger.error(f"خطا در Worker: {e}")
            time.sleep(300)  # 5 دقیقه انتظار

if __name__ == '__main__':
    main()
