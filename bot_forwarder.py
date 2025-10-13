import asyncio
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient, events

# === Load konfigurasi dari .env ===
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SOURCE_CHANNEL = int(os.getenv("SOURCE_CHANNEL"))
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL")

START_FROM_ID = int(os.getenv("START_FROM_ID", "0"))
INTERVAL_MINUTES = int(os.getenv("FORWARD_INTERVAL_MINUTES", "10"))
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

PROGRESS_FILE = Path("progress.json")

# === Variabel global ===
is_running = False
interval_minutes = INTERVAL_MINUTES
start_from_id = START_FROM_ID
last_sent_id = 0


# === Simpan & baca progress ===
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


# === Update .env ===
def update_env_var(key: str, value):
    os.environ[key] = str(value)
    if not os.path.exists(".env"):
        return
    lines, found = [], False
    with open(".env", "r") as f:
        for line in f:
            if line.startswith(f"{key}="):
                line = f"{key}={value}\n"
                found = True
            lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(".env", "w") as f:
        f.writelines(lines)


# === Proses forward pesan ===
async def forward_sequential(client: TelegramClient, source, target):
    global is_running, interval_minutes, start_from_id, last_sent_id

    last_saved = load_progress()
    # Jika ada perubahan start
    if start_from_id != 0 and start_from_id != last_saved:
        current_id = start_from_id
        save_progress(start_from_id)
    else:
        current_id = last_saved + 1 if last_saved > 0 else start_from_id

    print(f"▶️ Mulai forward dari ID: {current_id}")

    async for msg in client.iter_messages(source, reverse=True):
        if not is_running:
            print("⏸️ Forward dihentikan.")
            break
        if msg.id < current_id:
            continue
        if msg.action:
            continue
        try:
            await client.forward_messages(entity=target, messages=msg)
            last_sent_id = msg.id
            save_progress(last_sent_id)
            print(f"✅ Forwarded ID {msg.id}. Tunggu {interval_minutes} menit...")
            await asyncio.sleep(interval_minutes * 60)
        except Exception as e:
            print(f"[WARN] Gagal forward {msg.id}: {e}")

    print("✅ Semua postingan selesai di-forward.")


# === Fungsi utama ===
async def main():
    global is_running, interval_minutes, start_from_id, last_sent_id

    client = TelegramClient("session_bot_forwarder", API_ID, API_HASH)
    await client.start()

    source = await client.get_entity(SOURCE_CHANNEL)
    target = await client.get_entity(TARGET_CHANNEL)

    print("=" * 60)
    print("🚀 BOT FORWARDER (USER MODE + LINK START) AKTIF")
    print(f"📤 Sumber : {SOURCE_CHANNEL}")
    print(f"📥 Tujuan : {TARGET_CHANNEL}")
    print(f"▶️ Start ID : {start_from_id}")
    print(f"⏱️ Interval : {interval_minutes} menit antar postingan")
    print("=" * 60)

    # === Handler Command ===
    @client.on(events.NewMessage(from_users=OWNER_ID))
    async def command_handler(event):
        global is_running, interval_minutes, start_from_id, last_sent_id

        cmd = event.raw_text.strip()
        lower_cmd = cmd.lower()
        args = lower_cmd.split()

        # === /on ===
        if lower_cmd == "/on":
            if is_running:
                await event.reply("⚠️ Bot sudah berjalan.")
            else:
                is_running = True
                await event.reply("✅ Bot dimulai. Forward pesan berjalan...")
                asyncio.create_task(forward_sequential(client, source, target))

        # === /off ===
        elif lower_cmd == "/off":
            if not is_running:
                await event.reply("⚠️ Bot sudah berhenti.")
            else:
                is_running = False
                await event.reply("🛑 Bot dihentikan.")

        # === /setting ===
        elif lower_cmd.startswith("/setting"):
            if len(args) == 2 and args[1].isdigit():
                new_val = int(args[1])
                interval_minutes = new_val
                update_env_var("FORWARD_INTERVAL_MINUTES", new_val)
                await event.reply(f"✅ Interval diubah menjadi {new_val} menit.")

            elif len(args) == 3 and args[1] == "start" and args[2].isdigit():
                new_start = int(args[2])
                start_from_id = new_start
                update_env_var("START_FROM_ID", new_start)
                save_progress(start_from_id)
                await event.reply(f"✅ START_FROM_ID diubah ke {new_start}. Kirim /on untuk mulai.")
            else:
                await event.reply("⚙️ Format salah.\nGunakan:\n/setting <menit>\n/setting start <id>")

        # === /status ===
        elif lower_cmd == "/status":
            status = "🟢 Aktif" if is_running else "🔴 Nonaktif"
            last_id = load_progress()
            await event.reply(
                f"📊 Status: {status}\n"
                f"⏱️ Interval: {interval_minutes} menit\n"
                f"▶️ Start From ID: {start_from_id}\n"
                f"📨 Last ID: {last_id}"
            )

        # === /start <link> ===
        elif lower_cmd.startswith("/start "):
            match = re.search(r"https://t\.me/c/\d+/(\d+)", cmd)
            if match:
                new_start = int(match.group(1))
                start_from_id = new_start
                update_env_var("START_FROM_ID", new_start)
                save_progress(start_from_id)
                await event.reply(
                    f"✅ Titik mulai diatur ke **{new_start}**.\nKirim /on untuk memulai forward."
                )
            else:
                await event.reply("⚙️ Format salah.\nGunakan: /start https://t.me/c/<id_channel>/<id_pesan>")

        else:
            await event.reply("❓ Perintah tidak dikenali (/on, /off, /start <link>, /status, /setting)")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
