import os
import logging
import aiohttp
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
# It is recommended to set BOT_TOKEN in your environment variables on Render
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8884951959:AAGz_rHVNi38GJZXc1Y2W5JAlY06LDM1q8A")
CHANNEL_ID = -1003950743083
CHANNEL_INVITE_LINK = "https://t.me/protonxona_bot"  # Replace with actual private channel join link
AFFILIATE_LINK = "https://refpa3665.com/L?tag=d_6027237m_22179c_telegram_bot&site=6027237&ad=22179"
PROMO_CODE = "ml_3357479"
MIN_DEPOSIT_USD = 2.0  # Minimum required deposit amount
# -----------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

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

async def verify_user_deposit_via_api(account_id: str) -> tuple[bool, str]:
    """
    Automated check function for Affiliate API or local database verification.
    Replace this logic with an API endpoint call once provided by your manager.
    """
    # Example template for live API verification:
    # try:
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(f"https://api.yourdomain.com/verify?id={account_id}") as resp:
    #             if resp.status == 200:
    #                 data = await resp.json()
    #                 if data.get("has_deposited") and data.get("deposit_amount", 0) >= MIN_DEPOSIT_USD:
    #                     return True, "Verified"
    # except Exception as e:
    #     logging.error(f"API Error: {e}")

    # Default fallback: Returns False until connected to database or API
    return False, "Deposit record not found."

async def handle_account_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes submitted Account ID and triggers automated verification."""
    user_data = context.user_data

    if user_data.get("awaiting_account_id"):
        user_account_id = update.message.text.strip()
        user_data["awaiting_account_id"] = False

        await update.message.reply_text("🔍 Checking registration link and deposit balance ($2+)...")

        # Perform verification check
        is_verified, reason = await verify_user_deposit_via_api(user_account_id)

        if is_verified:
            # Automatic Access Granted
            await update.message.reply_text(
                "✅ **Verification Successful!**\n\n"
                f"We confirmed your registration and ${MIN_DEPOSIT_USD:.2f}+ deposit.\n"
                f"Click the link below to join the VIP Channel:\n{CHANNEL_INVITE_LINK}",
                parse_mode="Markdown"
            )
        else:
            # Automated Failure Handling
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

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Please configure it before starting.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^check_registration$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_id)
    )

    logging.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
