import os
import sys

import requests
from dotenv import load_dotenv

# โหลดค่าจาก .env (ห้าม hardcode token ลงในไฟล์นี้เด็ดขาด)
load_dotenv()


def get_chat_id():
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        print("❌ ไม่พบ TELEGRAM_TOKEN")
        print("👉 คัดลอก .env.example เป็น .env แล้วใส่ค่า TELEGRAM_TOKEN=<token ของคุณ>")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if "result" in data and len(data["result"]) > 0:
            # เอาข้อความล่าสุด
            latest_msg = data["result"][-1]
            chat_id = latest_msg["message"]["chat"]["id"]
            user_name = latest_msg["message"]["from"]["first_name"]
            print(f"\n✅ เจอแล้วครับเจ้านาย!")
            print(f"👤 ชื่อผู้ใช้: {user_name}")
            print(f"🆔 Chat ID ของคุณคือ: {chat_id}")
            print("------------------------------------------------")
            print("👉 เอาเลขนี้ไปใส่เป็น TELEGRAM_CHAT_ID ในไฟล์ .env ได้เลยครับ")
            print("⚠️  ตรวจสอบด้วยว่าเป็นชื่อ/เลขของคุณจริง — ใครก็ตามที่ทักบอทนี้")
            print("   จะโผล่มาที่นี่ได้เหมือนกัน")
        else:
            print("⏳ ยังไม่มีข้อความ... (เจ้านายทักแชทบอทไปหรือยังครับ?)")
    except Exception as e:
        # ตัด token ออกจากข้อความ error (requests จะแปะ URL เต็มๆ มาด้วย)
        print(f"❌ Error: {str(e).replace(token, '<TELEGRAM_TOKEN>')}")


if __name__ == "__main__":
    print("📡 กำลังค้นหาข้อความในบอท...")
    get_chat_id()
