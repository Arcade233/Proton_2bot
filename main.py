import logging
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
BOT_TOKEN = "8884951959:AAGz_rHVNi38GJZXc1Y2W5JAlY06LDM1q8A"
CHANNEL_ID = -1003950743083
CHANNEL_INVITE_LINK = "https://t.me/protonxona_bot"  # Replace with actual private channel link if needed
AFFILIATE_LINK = "https://refpa3665.com/L?tag=d_6027237m_22179c_telegram_bot&site=6027237&ad=22179"
PROMO_CODE = "ml_3357479"
ADMIN_USER_ID = 8965434188
# -----------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends welcome message and registration link."""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🔗 Register Here", url=AFFILIATE_LINK)],
        [InlineKeyboardButton("✅ I Have Registered", callback_data="check_registration")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"Hello {user.first_name}! 👋\n\n"
        f"To get access to our VIP Signal Channel, follow these simple steps:\n\n"
        f"1️⃣ Click the **Register Here** button below and create an account.\n"
        f"2️⃣ Make sure to use Promo Code: `{PROMO_CODE}`\n"
        f"3️⃣ Once registered, click **I Have Registered** below to verify."
    )
    
    await update.message.reply_text(
        welcome_text, parse_mode="Markdown", reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button clicks."""
    query = update.callback_query
    await query.answer()

    if query.data == "check_registration":
        await query.message.reply_text(
            "Please send me your registered **Account ID / User ID** so we can verify your account."
        )
        context.user_data["awaiting_account_id"] = True

async def handle_account_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captures the user's submitted ID and forwards it to the admin."""
    user_data = context.user_data

    if user_data.get("awaiting_account_id"):
        user_account_id = update.message.text.strip()
        user = update.effective_user
        
        user_data["awaiting_account_id"] = False

        admin_keyboard = [
            [
                InlineKeyboardButton("👍 Approve", callback_data=f"approve_{user.id}"),
                InlineKeyboardButton("👎 Reject", callback_data=f"reject_{user.id}"),
            ]
        ]
        
        await update.message.reply_text(
            "⏳ Your Account ID has been received! We are verifying your registration. "
            "You will receive your invite link shortly upon confirmation."
        )

        admin_text = (
            f"📥 **New Verification Request**\n\n"
            f"👤 **User:** {user.full_name} (@{user.username})\n"
            f"🆔 **Telegram ID:** `{user.id}`\n"
            f"🔢 **Submitted Account ID:** `{user_account_id}`"
        )
        
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=admin_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
        )

async def admin_approval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles admin approval or rejection buttons."""
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("_")
    target_user_id = int(user_id)

    if action == "approve":
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "✅ **Verification Successful!**\n\n"
                f"Welcome aboard! You can now join the VIP channel using this link:\n{CHANNEL_INVITE_LINK}"
            ),
        )
        await query.edit_message_text(f"{query.message.text}\n\n STATUS: APPROVED ✅")

    elif action == "reject":
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "❌ **Verification Failed.**\n\n"
                "We could not confirm your account registration with the provided ID. "
                "Please make sure you registered using our link and promo code, then try again."
            ),
        )
        await query.edit_message_text(f"{query.message.text}\n\n STATUS: REJECTED ❌")

def main():
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_approval, pattern="^(approve|reject)_"))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^check_registration$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_id)
    )

    logging.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
