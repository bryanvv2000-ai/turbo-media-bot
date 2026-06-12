import os
import logging
import sqlite3
from datetime import date
from telegram import (
    Update,
    LabeledPrice,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import yt_dlp

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]
FREE_DAILY_LIMIT = 5
STARS_PRICE = 50          # Telegram Stars for unlimited (30 days)
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = "users.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            downloads   INTEGER DEFAULT 0,
            last_date   TEXT    DEFAULT '',
            premium_until TEXT  DEFAULT ''
        )
    """)
    con.commit()
    con.close()

def get_user(user_id: int) -> dict:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT downloads, last_date, premium_until FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    if row is None:
        return {"downloads": 0, "last_date": "", "premium_until": ""}
    return {"downloads": row[0], "last_date": row[1], "premium_until": row[2]}

def update_user(user_id: int, downloads: int, last_date: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT INTO users (user_id, downloads, last_date)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET downloads=excluded.downloads, last_date=excluded.last_date
    """, (user_id, downloads, last_date))
    con.commit()
    con.close()

def set_premium(user_id: int, until: str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT INTO users (user_id, premium_until)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET premium_until=excluded.premium_until
    """, (user_id, until))
    con.commit()
    con.close()

def is_premium(user: dict) -> bool:
    pu = user.get("premium_until", "")
    if not pu:
        return False
    try:
        from datetime import date as _date
        return _date.fromisoformat(pu) >= _date.today()
    except Exception:
        return False

def can_download(user_id: int) -> tuple[bool, int]:
    """Returns (allowed, remaining_today)"""
    user = get_user(user_id)
    today = str(date.today())
    if is_premium(user):
        return True, 9999
    if user["last_date"] != today:
        update_user(user_id, 0, today)
        return True, FREE_DAILY_LIMIT
    remaining = FREE_DAILY_LIMIT - user["downloads"]
    return remaining > 0, max(remaining, 0)

def record_download(user_id: int):
    user = get_user(user_id)
    today = str(date.today())
    if user["last_date"] != today:
        update_user(user_id, 1, today)
    else:
        update_user(user_id, user["downloads"] + 1, today)

# ── Helpers ───────────────────────────────────────────────────────────────────
SUPPORTED_DOMAINS = (
    "youtube.com", "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com", "fb.watch",
    "twitter.com", "x.com",
)

def is_supported_url(text: str) -> bool:
    return any(d in text.lower() for d in SUPPORTED_DOMAINS)

def download_video(url: str, user_id: int) -> str | None:
    """Download best mp4 ≤ 50 MB; returns file path or None."""
    out_tmpl = os.path.join(DOWNLOAD_DIR, f"{user_id}_%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": out_tmpl,
        "format": "bestvideo[ext=mp4][filesize<50M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<50M]/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "cookiesfrombrowser": None,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info).replace(".webm", ".mp4").replace(".mkv", ".mp4")
    except Exception as e:
        logger.error("yt-dlp error: %s", e)
        return None

def cleanup(path: str):
    try:
        os.remove(path)
    except Exception:
        pass

# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Hola *{user.first_name}*!\n\n"
        "Soy *Turbo Media Downloader* 🚀\n"
        "Descargo videos de YouTube, TikTok, Instagram, Facebook y X/Twitter *sin marca de agua*.\n\n"
        "📋 *Cómo usarme:*\n"
        "Simplemente envíame el enlace del video que quieres descargar.\n\n"
        f"🎁 *Plan gratuito:* {FREE_DAILY_LIMIT} descargas por día.\n"
        f"⭐ *Premium:* ilimitado por {STARS_PRICE} Telegram Stars/mes.\n\n"
        "Comandos:\n"
        "/status — ver tus descargas de hoy\n"
        "/premium — obtener acceso ilimitado\n"
        "/help — ayuda"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start(update, ctx)

async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    today = str(date.today())
    if is_premium(user):
        msg = f"⭐ Eres *Premium* hasta `{user['premium_until']}`.\nDescargas: *ilimitadas* 🎉"
    else:
        used = user["downloads"] if user["last_date"] == today else 0
        remaining = FREE_DAILY_LIMIT - used
        msg = (
            f"📊 *Tu estado hoy:*\n"
            f"Usadas: {used}/{FREE_DAILY_LIMIT}\n"
            f"Restantes: {remaining}\n\n"
            f"¿Quieres más? /premium"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def premium_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("⭐ Comprar Premium (30 días)", callback_data="buy_premium")]]
    await update.message.reply_text(
        f"⭐ *Premium — Descargas ilimitadas por 30 días*\n\n"
        f"Precio: *{STARS_PRICE} Telegram Stars*\n\n"
        "Con Premium:\n"
        "✅ Descargas ilimitadas\n"
        "✅ Sin esperas\n"
        "✅ Soporte prioritario\n\n"
        "Presiona el botón para pagar:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def buy_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await ctx.bot.send_invoice(
        chat_id=query.from_user.id,
        title="Turbo Media Downloader Premium",
        description=f"Acceso ilimitado por 30 días — sin marca de agua",
        payload="premium_30d",
        currency="XTR",               # Telegram Stars
        prices=[LabeledPrice("Premium 30 días", STARS_PRICE)],
        provider_token="",             # vacío para Stars
    )

async def precheckout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload == "premium_30d":
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Pago no reconocido.")

async def successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from datetime import timedelta
    uid = update.effective_user.id
    until = str(date.today() + timedelta(days=30))
    set_premium(uid, until)
    await update.message.reply_text(
        f"🎉 *¡Pago exitoso! Ya eres Premium.*\n\n"
        f"Tu acceso ilimitado vence el *{until}*.\n"
        "¡Disfruta descargando sin límites! 🚀",
        parse_mode="Markdown",
    )

async def handle_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    uid = update.effective_user.id

    if not is_supported_url(url):
        await update.message.reply_text(
            "❌ URL no soportada.\n\n"
            "Plataformas compatibles: YouTube, TikTok, Instagram, Facebook, X/Twitter."
        )
        return

    allowed, remaining = can_download(uid)
    if not allowed:
        await update.message.reply_text(
            f"⛔ Has alcanzado tu límite de *{FREE_DAILY_LIMIT} descargas* gratuitas por hoy.\n\n"
            "Vuelve mañana o consigue acceso /premium ⭐",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text("⏳ Descargando... por favor espera.")

    path = download_video(url, uid)
    if path is None or not os.path.exists(path):
        await msg.edit_text("❌ No pude descargar ese video. Verifica el enlace e intenta de nuevo.")
        return

    file_size = os.path.getsize(path)
    if file_size > 50 * 1024 * 1024:
        cleanup(path)
        await msg.edit_text("❌ El video supera los 50 MB (límite de Telegram). Intenta con una versión más corta.")
        return

    record_download(uid)
    user_data = get_user(uid)

    try:
        await msg.edit_text("📤 Enviando video...")
        with open(path, "rb") as video_file:
            caption = "✅ ¡Aquí está tu video!\n"
            if not is_premium(user_data):
                today = str(date.today())
                used = user_data["downloads"] if user_data["last_date"] == today else 1
                left = FREE_DAILY_LIMIT - used
                caption += f"🎁 Descargas gratuitas restantes hoy: *{left}/{FREE_DAILY_LIMIT}*"
                if left <= 1:
                    caption += "\n⭐ ¿Quieres ilimitadas? /premium"
            await update.message.reply_video(video=video_file, caption=caption, parse_mode="Markdown")
        await msg.delete()
    except Exception as e:
        logger.error("Send error: %s", e)
        await msg.edit_text("❌ Error al enviar el video. Intenta de nuevo.")
    finally:
        cleanup(path)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("premium", premium_cmd))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_premium$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    logger.info("Bot iniciado ✅")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
