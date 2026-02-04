#!/usr/bin/env python3
"""
فایل اصلی اجرای ربات جنگ جهانی باستان
"""

import os
import sys

# اضافه کردن مسیر جاری به sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# اجرای برنامه اصلی
if __name__ == "__main__":
    from app import main
    
    try:
        print("🤖 شروع ربات جنگ جهانی باستان...")
        print(f"📁 مسیر دیتابیس: game.db")
        print(f"👑 مالک بازی: 8588773170")
        
        # اجرای برنامه
        main()
    except KeyboardInterrupt:
        print("\n🛑 ربات متوقف شد.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
