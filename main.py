import os
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta, timezone
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
CHANNEL_ID = -1003950743083  # Your numeric private VIP channel ID
AFFILIATE_LINK = "https://lkus.cc/6baca7"
PROMO_CODE = "ProX123"
MIN_DEPOSIT_USD = 2.0  # Minimum deposit requirement in USD
LINK_EXPIRE_MINUTES = 15  # Time limit for invite link
WEBHOOK_PORT = int(os.environ.get("PORT", 8080))
# -----------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- DATABASE SETUP ---
def init_db():
    """Initializes SQLite database."""
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversions (
            player_id TEXT PRIMARY KEY,
            deposit_amount REAL DEFAULT 0.0,
            registered INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def record_postback(player_id: str, amount: float):
    """Records or updates deposit/registration postbacks from 1win."""
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversions (player_id, deposit_amount, registered)
        VALUES (?, ?, 1)
        ON CONFLICT(player_id) DO UPDATE SET deposit_amount = deposit_amount + EXCLUDED.deposit_amount
    """, (player_id, amount))
    conn.commit()
    conn.close()

def check_account_exists(player_id: str) -> bool:
    """Step 1 Check: Checks if the Account ID registered under your link."""
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT registered FROM conversions WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    return True if row else False

def check_deposit_status(player_id: str) -> float:
    """Step 2 Check: Returns total deposit amount for the given Account ID."""
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT deposit_amount FROM conversions WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0

# --- DYNAMIC INVITE LINK GENERATOR ---
async def generate_expiring_invite_link(bot, user_id: int) -> str:
    """Generates a dynamic channel invite link that expires in 15 minutes."""
    expire_date = datetime.now(timezone.utc) + timedelta(minutes=LINK_EXPIRE_MINUTES)
    
    invite_link = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        expire_date=expire_date,
        member_limit=1,  # Single-use link
        name=f"VIP Access for {user_id}"
    )
    return invite_link.invite_link

# --- 1WIN S2S WEBHOOK HANDLER ---
async def handle_1win_postback(request: web.Request):
    """Processes postbacks triggered from 1win affiliate platform."""
    try:
        # 1win sends HTTP GET or POST requests
        params = request.query if request.method == "GET" else await request.json()
        
        # Flexibly extract player ID and deposit amount parameters
        player_id = params.get("player_id") or params.get("user_id") or params.get("subid") or params.get("sub_id")
        raw_amount = params.get("amount") or params.get("sum") or params.get("deposit") or 0.0
        amount = float(raw_amount)

        if player_id:
            record_postback(str(player_id).strip(), amount)
            logging.info(f"1win Postback received: Player ID {player_id} (Amount: ${amount:.2f})")
            return web.Response(text="OK", status=200)
        
        return web.Response(text="Missing player_id", status=400)
    except Exception as e:
        logging.error(f"1win Postback error: {e}")
        return web.Response(text="Error", status=500)

# --- TELEGRAM BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🔗 1. Register on 1win Here", url=AFFILIATE_LINK)],
        [InlineKeyboardButton("🆔 Step 1: Verify Account ID", callback_data="verify_account")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"Hello {user.first_name}! 👋\n\n"
        f"To gain instant access to our VIP Signal Channel, follow these steps:\n\n"
        f"1️⃣ Register using the button below with Promo Code: `{PROMO_CODE}`\n"
        f"2️⃣ Click **Step 1: Verify Account ID** to verify your registration.\n"
        f"3️⃣ Deposit at least **${MIN_DEPOSIT_USD:.2f}** to complete activation."
    )
    
    await update.message.reply_text(
        welcome_text, parse_mode="Markdown", reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify_account":
        await query.message.reply_text(
            "Please send your registered **1win Account ID / User ID**:"
        )
        context.user_data["awaiting_account_id"] = True

    elif query.data == "check_deposit":
        account_id = context.user_data.get("saved_account_id")
        if not account_id:
            await query.message.reply_text("Please enter your Account ID first by clicking /start.")
            return

        deposit_amount = check_deposit_status(account_id)
        if deposit_amount >= MIN_DEPOSIT_USD:
            expiring_link = await generate_expiring_invite_link(context.bot, query.from_user.id)
            
            keyboard = [[InlineKeyboardButton("🚀 Join VIP Channel Now", url=expiring_link)]]
            await query.message.reply_text(
                "🎉 **Deposit Confirmed!**\n\n"
                f"Deposit Total: **${deposit_amount:.2f}**\n\n"
                f"⏳ **Note:** Your access link below will expire in **{LINK_EXPIRE_MINUTES} minutes** and can only be used once.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 Re-check Deposit Status", callback_data="check_deposit")]
            ]
            await query.message.reply_text(
                f"⚠️ **Deposit Pending**\n\n"
                f"Account ID `{account_id}` is verified, but we have not detected a minimum deposit of **${MIN_DEPOSIT_USD:.2f}**.\n\n"
                f"Current Deposit Balance: **${deposit_amount:.2f}**\n\n"
                "Please make your deposit on 1win and tap **Re-check Deposit Status** below.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

async def handle_account_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if user_data.get("awaiting_account_id"):
        user_account_id = update.message.text.strip()
        user_data["awaiting_account_id"] = False

        await update.message.reply_text("🔍 Verifying 1win Account ID in database...")

        if check_account_exists(user_account_id):
            user_data["saved_account_id"] = user_account_id
            
            deposit_amount = check_deposit_status(user_account_id)
            
            if deposit_amount >= MIN_DEPOSIT_USD:
                expiring_link = await generate_expiring_invite_link(context.bot, update.effective_user.id)
                
                keyboard = [[InlineKeyboardButton("🚀 Join VIP Channel Now", url=expiring_link)]]
                await update.message.reply_text(
                    "✅ **Account & Deposit Confirmed!**\n\n"
                    f"Account ID `{user_account_id}` is active.\n\n"
                    f"⏳ **Note:** Your access link below will expire in **{LINK_EXPIRE_MINUTES} minutes** and can only be used once.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                keyboard = [
                    [InlineKeyboardButton("💵 Step 2: Check Deposit Status", callback_data="check_deposit")]
                ]
                await update.message.reply_text(
                    f"✅ **Step 1 Passed: Account ID Verified!**\n\n"
                    f"Account ID `{user_account_id}` was found.\n\n"
                    f"📌 **Step 2:** Please deposit at least **${MIN_DEPOSIT_USD:.2f}** into your 1win account.\n"
                    f"Once deposited, tap the button below to verify your deposit.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            keyboard = [
                [InlineKeyboardButton("🔗 Register Correctly on 1win", url=AFFILIATE_LINK)],
                [InlineKeyboardButton("🔄 Retry Account ID", callback_data="verify_account")]
            ]
            await update.message.reply_text(
                f"❌ **Account ID Not Found**\n\n"
                f"ID `{user_account_id}` was not found under our referral link.\n\n"
                f"Ensure you registered on 1win using our link with Promo Code `{PROMO_CODE}`.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

# --- DUAL-SERVICE RUNNER ---
async def main():
    init_db()

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Please configure it before starting.")
        
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(verify_account|check_deposit)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_id))

    web_app = web.Application()
    # Route postback to 1win handler
    web_app.router.add_route("*", "/postback", handle_1win_postback)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    logging.info(f"Webhook HTTP server started on port {WEBHOOK_PORT}")

    async with app:
        await app.start()
        await app.updater.start_polling()
        logging.info("Telegram Bot started successfully!")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
