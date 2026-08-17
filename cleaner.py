import os
import sys

# นามสกุลที่ถือว่าเป็นคลิป (ไฟล์อื่นจะไม่ถูกแตะ)
VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm")

# โฟลเดอร์ default ที่จะล้างชื่อ
DEFAULT_FOLDERS = ["MyReels", "MyReels2", "MyReels3"]


def clean_folder_names(folder_name, dry_run=True):
    """เปลี่ยนชื่อคลิปในโฟลเดอร์เป็น Ep001.mp4, Ep002.mp4, ...

    dry_run=True (ค่าเริ่มต้น) = แสดงผลเฉยๆ ไม่แตะไฟล์จริง
    """
    base_path = os.getcwd()
    target_folder = os.path.join(base_path, folder_name)

    mode = "DRY-RUN" if dry_run else "LIVE"
    print(f"🧹 [{mode}] Cleaning folder: {folder_name}...", flush=True)

    if not os.path.isdir(target_folder):
        print(f"❌ Not found: {target_folder}")
        return 0

    # แตะเฉพาะไฟล์วิดีโอ — ไม่ยุ่งกับ .py/.json/.env หรือไฟล์อื่นใดทั้งสิ้น
    files = sorted(
        f for f in os.listdir(target_folder)
        if os.path.isfile(os.path.join(target_folder, f))
        and f.lower().endswith(VIDEO_EXTS)
    )

    if not files:
        print(f"   ℹ️  ไม่มีคลิปในโฟลเดอร์นี้")
        return 0

    count = 0
    for i, filename in enumerate(files):
        ext = os.path.splitext(filename)[1].lower()
        new_name = f"Ep{str(i + 1).zfill(3)}{ext}"

        old_path = os.path.join(target_folder, filename)
        new_path = os.path.join(target_folder, new_name)

        if old_path == new_path:
            continue

        # os.rename บน Linux/macOS จะ "เขียนทับ" ไฟล์ปลายทางแบบเงียบๆ
        # ต้องเช็คก่อน ไม่งั้นคลิปหายถาวร
        if os.path.exists(new_path):
            print(f"   ⏭️  ข้าม {filename}: มี {new_name} อยู่แล้ว (กันไฟล์หาย)")
            continue

        if dry_run:
            print(f"   👀 จะเปลี่ยน: {filename} -> {new_name}")
            count += 1
            continue

        try:
            os.rename(old_path, new_path)
            print(f"   ✨ Renamed: {filename} -> {new_name}")
            count += 1
        except OSError as e:
            print(f"   ⚠️ Error renaming {filename}: {e}")

    verb = "จะเปลี่ยน" if dry_run else "เปลี่ยนแล้ว"
    print(f"✅ Finished! {verb} {count} videos in {folder_name}.\n")
    return count


def main():
    args = [a for a in sys.argv[1:] if a != "--apply"]
    dry_run = "--apply" not in sys.argv
    folders = args if args else DEFAULT_FOLDERS

    if dry_run:
        print("=" * 55)
        print("  โหมด DRY-RUN: ยังไม่แตะไฟล์จริง")
        print("  ถ้าผลลัพธ์ถูกต้องแล้ว ค่อยรันซ้ำด้วย --apply")
        print("=" * 55 + "\n")

    for folder in folders:
        clean_folder_names(folder, dry_run=dry_run)

    if dry_run:
        print("👉 รันจริง: python cleaner.py --apply")


if __name__ == "__main__":
    main()
