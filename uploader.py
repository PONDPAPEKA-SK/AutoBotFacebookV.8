import time
import os
import re
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from logger import BotLogger

# ชื่อ profile ที่ยอมรับได้: ตัวอักษร/ตัวเลข/ขีด/ขีดล่าง เท่านั้น
_SAFE_PROFILE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def safe_profile_path(profile_name, base_dir=None):
    """แปลงชื่อ profile เป็น path ที่ปลอดภัย

    กัน path traversal: ถ้าปล่อยให้ใส่ค่าอย่าง "../../Desktop" ตรงๆ
    Chrome จะไปสร้าง/เขียนทับ profile นอกโฟลเดอร์โปรเจกต์ และ cookie
    ของ Facebook จะไปโผล่ในที่ที่ .gitignore คุมไม่ถึง
    """
    if not _SAFE_PROFILE_RE.match(str(profile_name or "")):
        raise ValueError(
            f"ชื่อ profile ไม่ถูกต้อง: {profile_name!r} "
            "(ใช้ได้เฉพาะ A-Z a-z 0-9 _ - และยาวไม่เกิน 64 ตัว)"
        )
    base_dir = os.path.abspath(base_dir or os.getcwd())
    path = os.path.abspath(os.path.join(base_dir, profile_name))
    if os.path.commonpath([base_dir, path]) != base_dir:
        raise ValueError(f"profile path หลุดออกนอกโฟลเดอร์โปรเจกต์: {path}")
    return path


class FacebookReelsBot:
    def __init__(self, config, profile_name="bot_brain"):
        self.config = config
        self.profile_name = profile_name
        self.driver = None
        self.logger = BotLogger(log_dir="logs")

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def is_driver_alive(self):
        """ตรวจสอบว่า Chrome driver ยังทำงานอยู่ไหม"""
        if self.driver is None:
            return False
        try:
            _ = self.driver.title
            return True
        except Exception:
            return False

    def safe_quit(self):
        """ปิด Chrome อย่างปลอดภัย — ไม่พังแม้ driver ตายไปแล้ว"""
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception as e:
                self.log(f"⚠️ ปิด Chrome ไม่สำเร็จ (อาจปิดไปแล้ว): {e}")
            finally:
                self.driver = None

    def setup_driver(self):
        self.log(f">>> กำลังเปิด Chrome (Profile: {self.profile_name})...")
        try:
            options = webdriver.ChromeOptions()
            # ใช้ profile แยกแต่ละเพจ (ตรวจชื่อกัน path traversal ก่อน)
            profile_path = safe_profile_path(self.profile_name)
            options.add_argument(f"user-data-dir={profile_path}")
            # detach=False: ไม่ปล่อยให้ Chrome ที่ล็อกอิน Facebook ค้างเปิดทิ้งไว้
            # หลังสคริปต์จบ (ใครมานั่งหน้าเครื่องต่อก็ใช้ session ได้เลย)
            options.add_experimental_option("detach", False)
            options.add_argument("--disable-notifications")

            self.driver = webdriver.Chrome(options=options)
            self.driver.maximize_window()
        except Exception as e:
            self.log(f"❌ เปิด Chrome ไม่ได้: {e}")
            raise

    def safe_click(self, xpath, timeout=5):
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            element.click()
            return True
        except TimeoutException:
            return False
        except Exception as e:
            self.log(f"⚠️ safe_click ล้มเหลว ({xpath[:50]}): {e}")
            return False

    # ---------------------------------------------------------
    # 🛠️ ระบบสลับเพจ (ฉบับแก้ไข: ตัดตัวเช็ค Promote ออก)
    # ---------------------------------------------------------
    def handle_page_switch(self, page_url):
        driver = self.driver
        self.log(f"🔄 กำลังสลับเพจไปที่ URL: {page_url}")
        driver.get(page_url)
        time.sleep(5) 

        # --- ❌ ลบส่วนเช็คแอดมิน (Promote) ออกไปแล้วครับ ---
        # เพื่อป้องกันบอทสับสนเวลาเพจหลักมองเห็นเพจลูก

        self.log("👉 มองหาปุ่มสลับร่าง...")
        switch_found = False
        
        # รวม XPath ปุ่มสลับทุกแบบ
        switch_xpaths = [
            "//div[@role='button']//span[contains(text(), 'สลับ')]",
            "//div[@role='button']//span[contains(text(), 'Switch')]",
            "//div[contains(@aria-label, 'สลับ')]//span[contains(text(), 'สลับเลย')]",
            "//div[contains(@aria-label, 'Switch')]//span[contains(text(), 'Switch Now')]",
            "//div[@aria-label='สลับ' or @aria-label='Switch']",
            "//div[@aria-label='การดำเนินการเพิ่มเติม' or @aria-label='More actions']"
        ]

        for xpath in switch_xpaths:
            try:
                # ลดเวลาหาลงหน่อย จะได้ไม่รอนาน
                btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                
                # เช็คกันพลาด: ถ้าปุ่มมีคำว่าโปรโมท แสดงว่าไม่ใช่ปุ่มสลับ
                if "โปรโมท" in btn.text or "Promote" in btn.text:
                    continue

                driver.execute_script("arguments[0].click();", btn)
                self.log(f"   ✅ เจอปุ่มสลับแล้ว!")
                switch_found = True
                time.sleep(3)
                break
            except TimeoutException:
                continue
            except Exception as e:
                self.log(f"   ⚠️ ลองปุ่มสลับ xpath ไม่ผ่าน: {e}")
                continue

        if switch_found:
            self.log("👉 รอกดปุ่มยืนยัน...")
            try:
                confirm_xpath = "//div[@role='dialog']//div[@aria-label='สลับ' or @aria-label='Switch' or contains(@aria-label, 'Switch')]"
                confirm_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, confirm_xpath)))
                confirm_btn.click()
                self.log("   ✅ ยืนยันสลับร่างสำเร็จ!")
                time.sleep(8) 
            except TimeoutException:
                self.log("   ⚠️ ไม่เจอ Popup ยืนยัน (อาจจะสลับเรียบร้อยแล้ว)")
                time.sleep(5)
            except Exception as e:
                self.log(f"   ⚠️ กดยืนยันสลับมีปัญหา: {e}")
                time.sleep(5)
        else:
            self.log("ℹ️ ไม่เจอปุ่มสลับ (สมมติว่าอยู่ถูกเพจแล้ว หรือหาไม่เจอ)")
            driver.refresh()
            time.sleep(5)

    # ---------------------------------------------------------
    # 🛠️ ระบบโพสต์ (Force Click + ป้องกันกดผิด)
    # ---------------------------------------------------------
    def run_post_task(self, video_path, caption, page_url=None, category=None):
        driver = self.driver
        video_path = os.path.abspath(video_path) 
        self.log(f"🚀 เริ่มภารกิจ: {os.path.basename(video_path)}")

        try:
            # 1. เข้าหน้าสร้าง Reels
            self.log("⏳ เข้าหน้าสร้าง Reels...")
            driver.get("https://www.facebook.com/reels/create")
            time.sleep(8)

            # 2. อัปโหลดไฟล์
            self.log("⏳ กำลังอัปโหลดไฟล์...")
            upload_success = False
            try:
                elm = driver.find_element(By.XPATH, "//input[@type='file']")
                elm.send_keys(video_path)
                upload_success = True
            except Exception as e:
                self.logger.log_error(f"หาช่องอัปโหลดไม่เจอ: {e}", driver=self.driver)
                return False, "Input Not Found", None
            
            if not upload_success:
                return False, "Upload Failed", None

            self.log("⏳ รอคลิปโหลด (15 วิ)...")
            time.sleep(15) 

            # 3. กดถัดไป
            self.log("⏳ กดถัดไป...")
            if self.safe_click("//div[@role='dialog']//span[contains(text(), 'ถัดไป') or contains(text(), 'Next')]"):
                time.sleep(3)
            if self.safe_click("//div[@role='dialog']//span[contains(text(), 'ถัดไป') or contains(text(), 'Next')]"):
                time.sleep(5) 

            # 4. พิมพ์แคปชั่น
            if caption:
                self.log("✍️ พิมพ์แคปชั่น...")
                try:
                    actions = ActionChains(driver)
                    actions.send_keys(caption).perform()
                    time.sleep(2)
                except Exception as e:
                    self.logger.log_error(f"พิมพ์แคปชั่นไม่ได้: {e}", driver=self.driver)

            # 5. กดโพสต์ (Force Click)
            self.log("🚀 รอโหลดปุ่มโพสต์ (3 นาที)...")
            time.sleep(5) # รอ Copyright check

            try:
                wait = WebDriverWait(driver, 180)
                
                # หาปุ่มโพสต์ (ห้ามมีคำว่ากลุ่ม)
                possible_xpaths = [
                    "//div[@aria-label='โพสต์']",
                    "//div[@aria-label='Post']",
                    "//div[@role='button']//span[normalize-space(text())='โพสต์']",
                    "//div[@role='button']//span[normalize-space(text())='Post']"
                ]

                target_btn = None
                for xpath in possible_xpaths:
                    try:
                        btn = driver.find_element(By.XPATH, xpath)
                        if "กลุ่ม" not in btn.text and "Group" not in btn.text:
                            target_btn = btn
                            break
                    except Exception:
                        continue

                if not target_btn:
                    post_xpath = "//div[@role='button']//span[normalize-space(text())='โพสต์' or normalize-space(text())='Post']"
                    target_btn = wait.until(EC.element_to_be_clickable((By.XPATH, post_xpath)))

                self.log("⚡ สั่ง Force Click ปุ่มโพสต์!")
                driver.execute_script("arguments[0].click();", target_btn)

                self.log("🎉 โพสต์สำเร็จ!")
                time.sleep(15)
                return True, "Success", video_path
                
            except TimeoutException as e:
                 self.logger.log_error(f"รอนานเกิน ปุ่มโพสต์ไม่ขึ้น: {e}", driver=self.driver)
                 return False, "Timeout", None

        except Exception as e:
            self.logger.log_error(f"เกิดข้อผิดพลาดร้ายแรง: {e}", driver=self.driver)
            return False, str(e), None

    def move_to_posted(self, video_path, folder_path):
        try:
            posted_folder = os.path.join(folder_path, "posted")
            if not os.path.exists(posted_folder):
                os.makedirs(posted_folder)
            shutil.move(video_path, os.path.join(posted_folder, os.path.basename(video_path)))
            self.log(f"📦 ย้ายไฟล์เข้ากรุเรียบร้อย")
        except Exception as e:
            self.logger.log_error(f"ย้ายไฟล์ไม่ได้: {e}", driver=self.driver)