import os
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------------- CONFIGURATION ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", -1003950743083))
AFFILIATE_LINK = os.environ.get("AFFILIATE_LINK", "https://lkus.cc/6baca7")
PROMO_CODE = os.environ.get("PROMO_CODE", "ProX123")
MIN_DEPOSIT_USD = float(os.environ.get("MIN_DEPOSIT_USD", 2.0))
LINK_EXPIRE_MINUTES = int(os.environ.get("LINK_EXPIRE_MINUTES", 15))
WEBHOOK_PORT = int(os.environ.get("PORT", 8080))

if not BOT_TOKEN:
    raise ValueError("CRITICAL ERROR: 'BOT_TOKEN' environment variable is missing! Set it in Render dashboard.")
# -----------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- FAQ & MESSAGES ---
FAQ_DATA = {
    "faq_summary": (
        "📢 **ProtonXona VIP Channel: Full Summary & Description**\n\n"
        "Welcome to **ProtonXona VIP**, an automated AI signal and analytical hub for 1win players.\n\n"
        "🎯 **Core Capabilities & Features:**\n"
        "• **Automated AI Signals:** Real-time prediction data for popular games including **Aviator, Mines, and Coin Flip**.\n"
        "• **High-Accuracy Rate:** Targeted win rates reaching **95%+** through algorithmic analysis.\n"
        "• **Continuous 24/7 Dispatch:** Automated signal updates dispatched every **6 minutes**.\n"
        "• **Zero Subscription Fees:** Full access provided without recurring charges for registered community members.\n"
        "• **Direct Platform Sync:** Algorithms configured to operate alongside accounts registered with Promo Code `{promo}`.\n\n"
        "📌 *Use the navigation menu to review registration, deposit, and withdrawal guidelines before entering.*"
    ),
    "faq_register": (
        "❓ **How to Navigate & Register with Referral Link**\n\n"
        "1️⃣ Click on our official registration link: [Register Here]({link})\n"
        "2️⃣ Fill in your personal details (email, phone number, and strong password).\n"
        "3️⃣ Locate the **'Add Promo Code'** field during sign-up.\n"
        "4️⃣ Enter Promo Code: `{promo}` to activate VIP privileges and welcome bonuses.\n"
        "5️⃣ Complete the registration process and confirm your account."
    ),
    "faq_deposit": (
        "❓ **How to Deposit**\n\n"
        "1️⃣ Log in to your 1win account.\n"
        "2️⃣ Tap the **'Deposit'** button at the top right of the screen.\n"
        "3️⃣ Choose your preferred payment method (Mobile Money, Crypto, Bank Transfer, Visa/Mastercard).\n"
        "4️⃣ Enter an amount of at least **${min_dep:.2f}**.\n"
        "5️⃣ Follow the on-screen instructions to confirm your payment."
    ),
    "faq_why_link": (
        "❓ **Why Register & Deposit with Our Link & Promo Code?**\n\n"
        "• **VIP Signals Access:** Grants entry to our automated AI signal stream.\n"
        "• **Deposit Bonus:** Unlocks an exclusive welcome bonus on 1win using code `{promo}`.\n"
        "• **Algorithm Alignment:** Syncs your account ID with our prediction algorithms for optimal performance."
    ),
    "faq_about": (
        "❓ **What is the ProtonXona VIP Channel About?**\n\n"
        "🔥 **Features:**\n"
        "• **95%+ Win Rate:** High-accuracy automated AI signals.\n"
        "• **Supported Games:** Aviator, Mines, and Coin Flip.\n"
        "• **24/7 Coverage:** Live prediction updates dispatched every 6 minutes.\n"
        "• **Zero Monthly Fees:** Free access for registered members."
    ),
    "faq_withdraw": (
        "❓ **How to Withdraw Your Winnings**\n\n"
        "1️⃣ Open your 1win account profile and select **'Withdrawal'**.\n"
        "2️⃣ Select the payment method (must match your deposit method or verified account details).\n"
        "3️⃣ Enter the desired withdrawal amount and confirm.\n"
        "⚡ *Withdrawals are typically processed within a few minutes to 24 hours depending on the chosen method.*"
    )
}

# --- INVITE LINK GENERATION ---
async def generate_expiring_invite_link(bot, user_id: int) -> str:
    expire_date = datetime.now(timezone.utc) + timedelta(minutes=LINK_EXPIRE_MINUTES)
    invite_link = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        expire_date=expire_date,
        member_limit=1,
        name=f"VIP Access for {user_id}"
    )
    return invite_link.invite_link

# --- KEYBOARD BUILDERS ---
def build_main_keyboard(invite_url: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📢 Channel Description & Overview", callback_data="faq_summary")],
        [InlineKeyboardButton("📲 How to Register", callback_data="faq_register")],
        [InlineKeyboardButton("💵 How to Deposit", callback_data="faq_deposit")],
        [InlineKeyboardButton("⭐ Why Use My Link & Code?", callback_data="faq_why_link")],
        [InlineKeyboardButton("ℹ️ What is Channel About?", callback_data="faq_about")],
        [InlineKeyboardButton("💳 How to Withdraw", callback_data="faq_withdraw")],
        [InlineKeyboardButton("🚀 Join VIP Channel Now", url=invite_url)]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_faq")]
    ])

# --- TELEGRAM HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        expiring_link = await generate_expiring_invite_link(context.bot, user_id)
        context.user_data["last_invite_link"] = expiring_link
        
        welcome_text = (
            "👋 **Welcome to the ProtonXona VIP Access Portal!**\n\n"
            "🔥 **VIP Channel Overview:**\n"
            "• **95%+ Win Rate:** Automated AI signals for Aviator, Mines, & Coin Flip.\n"
            "• **24/7 Coverage:** Live updates every 6 minutes.\n"
            "• **100% Free Access:** Instant entry via the link below.\n\n"
            "📖 **Frequently Asked Questions:**\n"
            "Explore the channel summary and FAQs below for guidance on registration and features.\n\n"
            f"⏳ **Your VIP Access Link:**\n"
            f"Your temporary link expires in **{LINK_EXPIRE_MINUTES} minutes** and is for single-use."
        )
        
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=build_main_keyboard(expiring_link)
        )
    except Exception as e:
        logging.error(f"Error generating invite link: {e}")
        await update.message.reply_text("⚠️ An error occurred while generating your invite link. Make sure the bot is an admin in the channel.")

async def handle_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data in FAQ_DATA:
        text = FAQ_DATA[data].format(
            link=AFFILIATE_LINK,
            promo=PROMO_CODE,
            min_dep=MIN_DEPOSIT_USD
        )
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=build_back_keyboard()
        )
    elif data == "back_to_faq":
        invite_link = context.user_data.get("last_invite_link", AFFILIATE_LINK)
        welcome_text = (
            "👋 **ProtonXona VIP Access Portal**\n\n"
            "Select an FAQ option below, or use your temporary invite link to enter the VIP channel:\n\n"
            f"⏳ **Note:** Your access link expires **{LINK_EXPIRE_MINUTES} minutes** after creation."
        )
        await query.message.edit_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=build_main_keyboard(invite_link)
        )

# --- DUMMY WEBHOOK FOR RENDER HEALTH CHECKS ---
async def handle_health_check(request: web.Request):
    return web.Response(text="Bot is healthy and running.", status=200)

# --- APPLICATION RUNNER ---
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_faq_callback, pattern="^(faq_|back_to_faq)"))

    web_app = web.Application()
    web_app.router.add_route("*", "/", handle_health_check)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    logging.info(f"Health check server active on port {WEBHOOK_PORT}")

    async with app:
        await app.start()
        await app.updater.start_polling()
        logging.info("Telegram Bot actively listening for messages...")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
