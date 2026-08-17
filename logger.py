import os
import glob
import re
from datetime import datetime

# จำนวนไฟล์ log สูงสุดที่เก็บไว้ (เก่าสุดจะถูกลบ)
MAX_LOG_FILES = 30

# รูปแบบ Telegram bot token: <digits>:<35 ตัวอักษร>
# หมายเหตุ: ห้ามใส่ \b ข้างหน้า เพราะใน URL จริงจะเป็น ".../bot8429667497:AA..."
# ซึ่ง "bot" กับตัวเลขติดกันเป็นคำเดียว ทำให้ \b ไม่ match
_TELEGRAM_TOKEN_RE = re.compile(r"\d{6,12}:[A-Za-z0-9_-]{30,}")


def redact_secrets(text):
    """ตัดค่าลับออกจากข้อความก่อน print/เขียนลง log

    สำคัญมาก: exception ของ requests จะแปะ URL เต็มๆ มาด้วย ซึ่ง URL ของ
    Telegram API มี bot token อยู่ในนั้น (https://api.telegram.org/bot<TOKEN>/...)
    ถ้า print ตรงๆ = token หลุดลง log/หน้าจอ dashboard ทันที
    """
    if not text:
        return text
    text = str(text)

    # ลำดับสำคัญมาก! ต้องตัด token แบบ pattern ก่อน
    # ถ้าเอา chat_id (ตัวเลขสั้นๆ) ไปแทนก่อน มันจะไปโดนตัวเลขที่อยู่กลาง token
    # ทำให้ token ขาดเป็นท่อน แล้ว regex จับไม่ได้ → token หลุดบางส่วน
    # 1) ตัดอะไรก็ตามที่หน้าตาเหมือน Telegram token
    text = _TELEGRAM_TOKEN_RE.sub("<REDACTED_TOKEN>", text)

    # 2) ตัด token ที่รู้ค่าแน่นอนจาก environment (เผื่อรูปแบบไม่ตรง pattern)
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if token and len(token) >= 8:
        text = text.replace(token, "<TELEGRAM_TOKEN>")

    # 3) chat_id เป็นตัวเลขสั้น — ต้องแทนเฉพาะตอนที่ยืนอยู่เดี่ยวๆ
    #    ไม่งั้นจะไปโดนตัวเลขอื่นที่บังเอิญมี chat_id เป็นส่วนหนึ่ง
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if chat_id and len(chat_id) >= 5:
        text = re.sub(rf"(?<!\d){re.escape(chat_id)}(?!\d)", "<TELEGRAM_CHAT_ID>", text)

    return text

class BotLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self._cleanup_old_logs()

    def _get_log_filepath(self):
        """สร้าง path ไฟล์ log ของวันนี้"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"bot_{today}.log")

    def _write_to_file(self, line):
        """เขียน 1 บรรทัดลงไฟล์ log ของวันนี้"""
        try:
            with open(self._get_log_filepath(), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[LOG FILE ERROR] เขียน log ไม่ได้: {e}")

    def _cleanup_old_logs(self):
        """ลบไฟล์ log เก่าที่เกิน MAX_LOG_FILES ไฟล์"""
        try:
            log_files = sorted(glob.glob(os.path.join(self.log_dir, "bot_*.log")))
            if len(log_files) > MAX_LOG_FILES:
                for old_file in log_files[:len(log_files) - MAX_LOG_FILES]:
                    os.remove(old_file)
        except Exception as e:
            print(f"[LOG CLEANUP] ลบ log เก่าไม่ได้: {e}")

    def log(self, message):
        """Prints message with timestamp + เขียนลงไฟล์"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = redact_secrets(f"[{timestamp}] {message}")
        print(line)
        self._write_to_file(line)

    def log_error(self, message, driver=None):
        """
        Logs error message + เขียนลงไฟล์ + ถ่าย screenshot ถ้ามี driver
        Returns screenshot path if saved, else None.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = redact_secrets(f"[ERROR] [{timestamp}] {message}")
        print(line)
        self._write_to_file(line)

        screenshot_path = None

        if driver:
            try:
                filename = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                screenshot_path = os.path.join(self.log_dir, filename)
                driver.save_screenshot(screenshot_path)
                ss_msg = f"[SCREENSHOT] {screenshot_path}"
                print(ss_msg)
                self._write_to_file(ss_msg)
            except Exception as e:
                err_msg = f"[SCREENSHOT FAILED] {e}"
                print(err_msg)
                self._write_to_file(err_msg)
                screenshot_path = None

        return screenshot_path
