import os
import sqlite3
import logging
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIGURATION ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8884951959:AAGz_rHVNi38GJZXc1Y2W5JAlY06LDM1q8A")
CHANNEL_ID = -1003950743083
CHANNEL_INVITE_LINK = "https://t.me/protonxona_bot"  # Replace with your actual private channel invite link
AFFILIATE_LINK = "https://refpa3665.com/L?tag=d_6027237m_22179c_telegram_bot&site=6027237&ad=22179"
PROMO_CODE = "ml_3357479"
MIN_DEPOSIT_USD = 3.0  # Minimum deposit requirement in USD
WEBHOOK_PORT = int(os.environ.get("PORT", 8080))  # Binds to Render's dynamic port to prevent timeout
# -----------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- DATABASE SETUP ---
def init_db():
    """Initializes SQLite database to store MelBet postback conversions."""
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversions (
            player_id TEXT PRIMARY KEY,
            deposit_amount REAL,
            verified INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def record_postback(player_id: str, amount: float):
    """Records or updates deposit postbacks received from MelBet."""
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversions (player_id, deposit_amount, verified)
        VALUES (?, ?, 0)
        ON CONFLICT(player_id) DO UPDATE SET deposit_amount = deposit_amount + EXCLUDED.deposit_amount
    """, (player_id, amount))
    conn.commit()
    conn.close()

def check_player_status(player_id: str) -> bool:
    """Checks whether the given player ID has met the minimum deposit requirement."""
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT deposit_amount FROM conversions WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] >= MIN_DEPOSIT_USD:
        return True
    return False

# --- MELBET WEBHOOK HANDLER ---
async def handle_melbet_postback(request: web.Request):
    """
    Endpoint: https://your-service.onrender.com/postback?player_id={player_id}&amount={amount}
    """
    try:
        params = request.query if request.method == "GET" else await request.json()
        
        player_id = params.get("player_id") or params.get("subid") or params.get("userid")
        raw_amount = params.get("amount") or params.get("deposit") or 0.0
        amount = float(raw_amount)

        if player_id:
            record_postback(str(player_id).strip(), amount)
            logging.info(f"Postback received: Player ID {player_id} deposited ${amount:.2f}")
            return web.Response(text="OK", status=200)
        
        return web.Response(text="Missing player_id", status=400)
    except Exception as e:
        logging.error(f"Postback error: {e}")
        return web.Response(text="Error", status=500)

# --- TELEGRAM BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends welcome message with registration instructions."""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🔗 1. Register Account Here", url=AFFILIATE_LINK)],
        [InlineKeyboardButton("✅ I Have Registered & Deposited $2+", callback_data="check_registration")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"Hello {user.first_name}! 👋\n\n"
        f"To gain instant access to our VIP Signal Channel, follow these steps:\n\n"
        f"1️⃣ Click **Register Account Here** below to create your account.\n"
        f"2️⃣ Make sure to use Promo Code: `{PROMO_CODE}`\n"
        f"3️⃣ Deposit a minimum of **${MIN_DEPOSIT_USD:.2f}** into your new account.\n"
        f"4️⃣ Click **I Have Registered & Deposited $2+** below to verify."
    )
    
    await update.message.reply_text(
        welcome_text, parse_mode="Markdown", reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles verification button click."""
    query = update.callback_query
    await query.answer()

    if query.data == "check_registration":
        await query.message.reply_text(
            "Please enter and send your registered **Account ID / User ID** so the system can verify your registration and deposit."
        )
        context.user_data["awaiting_account_id"] = True

async def handle_account_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes submitted Account ID and triggers automated database verification."""
    user_data = context.user_data

    if user_data.get("awaiting_account_id"):
        user_account_id = update.message.text.strip()
        user_data["awaiting_account_id"] = False

        await update.message.reply_text("🔍 Checking registration link and deposit balance ($2+)...")

        # Perform database verification check from received postbacks
        if check_player_status(user_account_id):
            await update.message.reply_text(
                "✅ **Verification Successful!**\n\n"
                f"We confirmed your registration and ${MIN_DEPOSIT_USD:.2f}+ deposit.\n"
                f"Click the link below to join the VIP Channel:\n{CHANNEL_INVITE_LINK}",
                parse_mode="Markdown"
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔗 Register Correctly", url=AFFILIATE_LINK)],
                [InlineKeyboardButton("🔄 Retry Verification", callback_data="check_registration")]
            ]
            await update.message.reply_text(
                f"❌ **Verification Unsuccessful**\n\n"
                f"Reason: System could not confirm a minimum ${MIN_DEPOSIT_USD:.2f} deposit under ID `{user_account_id}`.\n\n"
                f"Ensure you registered using our link, used Promo Code `{PROMO_CODE}`, and deposited at least ${MIN_DEPOSIT_USD:.2f}.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

# --- DUAL-SERVICE RUNNER ---
async def main():
    """Initializes DB, starts Webhook Server, and runs Telegram Bot simultaneously."""
    init_db()

    # 1. Initialize Telegram Application
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Please configure it before starting.")
        
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^check_registration$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_id))

    # 2. Initialize Webhook HTTP Server on Render's Port
    web_app = web.Application()
    web_app.router.add_route("*", "/postback", handle_melbet_postback)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    
    # Binds server to 0.0.0.0 and PORT variable so Render doesn't time out
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    logging.info(f"Webhook HTTP server started on port {WEBHOOK_PORT}")

    # 3. Start Telegram Bot Polling concurrently
    async with app:
        await app.start()
        await app.updater.start_polling()
        logging.info("Telegram Bot started successfully!")
        
        # Keep execution alive
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
