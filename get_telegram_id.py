import requests
import time

# เอา Token ที่ได้จาก BotFather มาใส่ตรงนี้
TOKEN = "7957078815:AAEsoM5WMWoYCZv41NvSewa6N9NpLRHgYUM"

def get_chat_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        response = requests.get(url)
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
            print("👉 เอาเลขนี้ไปใส่ใน bot.py ได้เลยครับ!")
        else:
            print("⏳ ยังไม่ข้อความ... (เจ้านายทักแชทบอทไปหรือยังครับ?)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print(f"📡 กำลังค้นหาข้อความในบอท...")
    get_chat_id()