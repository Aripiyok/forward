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
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL")
START_FROM_ID = int(os.getenv("START_FROM_ID", "0"))
INTERVAL_MINUTES = int(os.getenv("FORWARD_INTERVAL_MINUTES", "10"))

PROGRESS_FILE = Path("progress.json")

def load_progress() -> int:
    """Ambil ID pesan terakhir dari file progress"""
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            return int(data.get("last_id", 0))
        except Exception:
            return 0
    return 0

def save_progress(last_id: int):
    """Simpan ID terakhir yang sudah di-forward"""
    PROGRESS_FILE.write_text(json.dumps({"last_id": last_id}), encoding="utf-8")

async def forward_sequential(client: TelegramClient, source, target):
    """Forward pesan satu per satu dengan jeda antar posting"""
    last_id = load_progress()
    min_id = max(last_id, START_FROM_ID)
    newest_id = min_id

    async for msg in client.iter_messages(source, reverse=True, min_id=min_id):
        if msg.action:  # lewati join/leave/pin messages
            continue
        try:
            await client.forward_messages(entity=target, messages=msg)
            newest_id = msg.id
            save_progress(newest_id)
            print(f"✅ Forwarded message ID {msg.id}. Tunggu {INTERVAL_MINUTES} menit sebelum lanjut...")
            await asyncio.sleep(INTERVAL_MINUTES * 60)
        except Exception as e:
            print(f"[WARN] Gagal forward msg {msg.id}: {e}")

    print("✅ Semua postingan sudah di-forward. Selesai.")

async def main():
    client = TelegramClient("session_single_forwarder", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    source = await client.get_entity(SOURCE_CHANNEL)
    target = await client.get_entity(TARGET_CHANNEL)

    print("=" * 60)
    print("🚀 BOT FORWARDER (SATUAN PER INTERVAL) AKTIF")
    print(f"📤 Sumber : {SOURCE_CHANNEL}")
    print(f"📥 Tujuan : {TARGET_CHANNEL}")
    print(f"▶️ Mulai dari ID : {max(START_FROM_ID, load_progress())}")
    print(f"⏱️ Interval : {INTERVAL_MINUTES} menit antar postingan")
    print("=" * 60)

    await forward_sequential(client, source, target)

if __name__ == "__main__":
    asyncio.run(main())
