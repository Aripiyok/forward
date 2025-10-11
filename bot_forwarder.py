import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient

# === Load konfigurasi dari file .env ===
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Tidak pakai BOT_TOKEN karena kita login sebagai user
SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL"))
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL")

START_FROM_ID = int(os.getenv("START_FROM_ID", "0"))
INTERVAL_MINUTES = int(os.getenv("FORWARD_INTERVAL_MINUTES", "10"))

PROGRESS_FILE = Path("progress.json")

# === Fungsi untuk simpan & baca progress ===
def load_progress() -> int:
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            return int(data.get("last_id", 0))
        except Exception:
            return 0
    return 0


def save_progress(last_id: int):
    PROGRESS_FILE.write_text(json.dumps({"last_id": last_id}), encoding="utf-8")


# === Fungsi utama untuk forward pesan satu per satu ===
async def forward_sequential(client: TelegramClient, source, target):
    last_id = load_progress()
    min_id = max(last_id, START_FROM_ID)
    newest_id = min_id

    async for msg in client.iter_messages(source, reverse=True, min_id=min_id):
        if msg.action:
            continue
        try:
            await client.forward_messages(entity=target, messages=msg)
            newest_id = msg.id
            save_progress(newest_id)
            print(
                f"✅ Forwarded message ID {msg.id}. Tunggu {INTERVAL_MINUTES} menit sebelum lanjut..."
            )
            await asyncio.sleep(INTERVAL_MINUTES * 60)
        except Exception as e:
            print(f"[WARN] Gagal forward msg {msg.id}: {e}")

    print("✅ Semua postingan sudah di-forward. Selesai.")


# === Fungsi utama untuk menjalankan client ===
async def main():
    client = TelegramClient("session_bot_forwarder", API_ID, API_HASH)
    await client.start()  # login pakai akun user (bukan bot token)

    source = await client.get_entity(SOURCE_CHANNEL)
    target = await client.get_entity(TARGET_CHANNEL)

    print("=" * 60)
    print("🚀 BOT FORWARDER (AKUN USER MODE) AKTIF")
    print(f"📤 Sumber : {SOURCE_CHANNEL}")
    print(f"📥 Tujuan : {TARGET_CHANNEL}")
    print(f"▶️ Mulai dari ID : {max(START_FROM_ID, load_progress())}")
    print(f"⏱️ Interval : {INTERVAL_MINUTES} menit antar postingan")
    print("=" * 60)

    await forward_sequential(client, source, target)


if __name__ == "__main__":
    asyncio.run(main())
