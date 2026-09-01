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
# Fetches securely from Render Environment Variables
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

# --- MULTI-LANGUAGE TRANSLATIONS ---
TEXTS = {
    "en": {
        "welcome": (
            "👋 **Welcome to the ProtonXona VIP Access Portal!**\n\n"
            "🔥 **About Our VIP Channel:**\n"
            "• **95%+ Win Rate:** Automated AI signals for Aviator, Mines, & Coin Flip.\n"
            "• **24/7 Coverage:** Live updates every 6 minutes.\n"
            "• **100% Free Access:** Exclusive for registered members.\n\n"
            "📋 **How to Join:**\n"
            "1️⃣ Tap **Register on 1win** using Promo Code: `{promo}`\n"
            "2️⃣ Tap **Step 1: Verify Registration** to confirm your Account ID.\n"
            "3️⃣ Tap **Step 2: Verify Deposit** after depositing at least **${min_dep:.2f}**."
        ),
        "btn_reg_link": "🔗 1. Register on 1win Here",
        "btn_step1": "🆔 Step 1: Verify Registration",
        "btn_step2": "💵 Step 2: Verify Deposit",
        "btn_lang": "🌐 Switch Language / Changer de langue",
        "prompt_id": "Please reply with your registered **1win Account ID / Player ID**:",
        "verifying_db": "🔍 Checking registration records in database...",
        "reg_success": (
            "✅ **Step 1 Passed: Account ID Verified!**\n\n"
            "Account ID `{id}` is bound to your Telegram account.\n\n"
            "📌 **Next Step:** Deposit at least **${min_dep:.2f}** on 1win, then click **Step 2: Verify Deposit** below."
        ),
        "reg_failed": (
            "❌ **Registration Not Found**\n\n"
            "Account ID `{id}` was not found in our database.\n\n"
            "Make sure you registered on 1win using our link with Promo Code `{promo}`."
        ),
        "already_claimed_other": (
            "⚠️ **Account ID Already Bound!**\n\n"
            "The Account ID `{id}` has already been verified by another Telegram user."
        ),
        "dep_success": (
            "🎉 **Deposit Confirmed! VIP Unlocked!**\n\n"
            "Total Deposit Balance: **${amount:.2f}**\n\n"
            "⏳ **Note:** Your access link below will expire in **{mins} minutes** and can only be used once."
        ),
        "already_issued": (
            "🔒 **Invite Link Already Issued**\n\n"
            "You have already generated an invite link for Account ID `{id}`."
        ),
        "dep_pending": (
            "⚠️ **Deposit Pending**\n\n"
            "Account ID `{id}` is verified, but we have not detected a deposit of at least **${min_dep:.2f}**.\n\n"
            "Current Balance: **${amount:.2f}**\n\n"
            "Please complete your deposit on 1win and tap **Re-check Deposit** below."
        ),
        "no_id_saved": "Please verify your Account ID first by tapping **Step 1: Verify Registration**.",
        "btn_join": "🚀 Join VIP Channel Now",
        "btn_recheck": "🔄 Re-check Deposit Status",
        "btn_retry_id": "🔄 Retry Account ID",
        "lang_selected": "🌐 Language set to **English**."
    },
    "fr": {
        "welcome": (
            "👋 **Bienvenue sur le Portail d'Accès ProtonXona VIP!**\n\n"
            "🔥 **À propos de notre Canal VIP:**\n"
            "• **+95% de réussite:** Signaux IA automatisés pour Aviator, Mines, et Coin Flip.\n"
            "• **Couverture 24/7:** Mises à jour en direct toutes les 6 minutes.\n"
            "• **Accès 100% Gratuit:** Exclusif pour nos membres inscrits.\n\n"
            "📋 **Comment rejoindre:**\n"
            "1️⃣ Cliquez sur **S'inscrire sur 1win** avec le Code Promo: `{promo}`\n"
            "2️⃣ Cliquez sur **Étape 1: Vérifier Inscription** pour valider votre ID.\n"
            "3️⃣ Cliquez sur **Étape 2: Vérifier Dépôt** après un dépôt d'au moins **${min_dep:.2f}**."
        ),
        "btn_reg_link": "🔗 1. S'inscrire sur 1win Ici",
        "btn_step1": "🆔 Étape 1: Vérifier Inscription",
        "btn_step2": "💵 Étape 2: Vérifier Dépôt",
        "btn_lang": "🌐 Switch Language / Changer de langue",
        "prompt_id": "Veuillez répondre avec votre **ID de Compte 1win / ID Joueur**:",
        "verifying_db": "🔍 Vérification de l'inscription dans la base de données...",
        "reg_success": (
            "✅ **Étape 1 Validée: Compte Inscrit!**\n\n"
            "L'ID `{id}` est bien inscrit et lié à votre compte Telegram.\n\n"
            "📌 **Prochaine Étape:** Déposez au moins **${min_dep:.2f}** sur votre compte 1win, puis cliquez sur **Étape 2: Vérifier Dépôt** ci-dessous."
        ),
        "reg_failed": (
            "❌ **Inscription Non Trouvée**\n\n"
            "L'ID `{id}` n'a pas été trouvé dans notre base de données.\n\n"
            "Assurez-vous de vous être inscrit sur 1win via notre lien avec le Code Promo `{promo}`."
        ),
        "already_claimed_other": (
            "⚠️ **ID de Compte Déjà Utilisé!**\n\n"
            "L'ID 1win `{id}` a déjà été vérifié par un autre utilisateur Telegram."
        ),
        "dep_success": (
            "🎉 **Dépôt Confirmé! Accès VIP Débloqué!**\n\n"
            "Total des dépôts: **${amount:.2f}**\n\n"
            "⏳ **Note:** Votre lien d'accès expirera dans **{mins} minutes** et est à usage unique."
        ),
        "already_issued": (
            "🔒 **Lien d'invitation Déjà Généré**\n\n"
            "Vous avez déjà généré un lien d'invitation pour l'ID `{id}`."
        ),
        "dep_pending": (
            "⚠️ **Dépôt En Attente**\n\n"
            "L'ID `{id}` est vérifié, mais nous n'avons pas détecté un dépôt minimum de **${min_dep:.2f}**.\n\n"
            "Solde Actuel: **${amount:.2f}**\n\n"
            "Veuillez effectuer un dépôt sur 1win et cliquer sur **Re-vérifier le Dépôt**."
        ),
        "no_id_saved": "Veuillez d'abord vérifier votre ID en cliquant sur **Étape 1: Vérifier Inscription**.",
        "btn_join": "🚀 Rejoindre le Canal VIP",
        "btn_recheck": "🔄 Re-vérifier le Dépôt",
        "btn_retry_id": "🔄 Réessayer l'ID",
        "lang_selected": "🌐 Langue changée en **Français**."
    }
}

# --- DATABASE SETUP & HELPERS ---
def init_db():
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversions (
            player_id TEXT PRIMARY KEY,
            deposit_amount REAL DEFAULT 0.0,
            registered INTEGER DEFAULT 1,
            claimed_by_telegram_id INTEGER DEFAULT NULL,
            invite_claimed INTEGER DEFAULT 0
        )
    """)
    # Migration safeguard for legacy databases
    cursor.execute("PRAGMA table_info(conversions)")
    columns = [column[1] for column in cursor.fetchall()]
    if "claimed_by_telegram_id" not in columns:
        cursor.execute("ALTER TABLE conversions ADD COLUMN claimed_by_telegram_id INTEGER DEFAULT NULL")
    if "invite_claimed" not in columns:
        cursor.execute("ALTER TABLE conversions ADD COLUMN invite_claimed INTEGER DEFAULT 0")
        
    conn.commit()
    conn.close()

def record_postback(player_id: str, amount: float):
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversions (player_id, deposit_amount, registered)
        VALUES (?, ?, 1)
        ON CONFLICT(player_id) DO UPDATE SET deposit_amount = deposit_amount + EXCLUDED.deposit_amount
    """, (player_id, amount))
    conn.commit()
    conn.close()

def attempt_claim_account(player_id: str, telegram_id: int) -> str:
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT claimed_by_telegram_id FROM conversions WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return "not_found"

    existing_claimer = row[0]

    if existing_claimer is None:
        cursor.execute("UPDATE conversions SET claimed_by_telegram_id = ? WHERE player_id = ?", (telegram_id, player_id))
        conn.commit()
        conn.close()
        return "success"
    elif existing_claimer == telegram_id:
        conn.close()
        return "already_owned"
    else:
        conn.close()
        return "claimed_by_other"

def check_deposit_status(player_id: str) -> tuple[float, int]:
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT deposit_amount, invite_claimed FROM conversions WHERE player_id = ?", (player_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return 0.0, 0

def mark_invite_as_issued(player_id: str):
    conn = sqlite3.connect("affiliate_data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE conversions SET invite_claimed = 1 WHERE player_id = ?", (player_id,))
    conn.commit()
    conn.close()

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

# --- WEBHOOK ENDPOINT FOR S2S POSTBACKS ---
async def handle_1win_postback(request: web.Request):
    try:
        params = request.query if request.method == "GET" else await request.json()
        player_id = params.get("player_id") or params.get("user_id") or params.get("subid") or params.get("sub_id")
        raw_amount = params.get("amount") or params.get("sum") or params.get("deposit") or 0.0
        amount = float(raw_amount)

        if player_id:
            record_postback(str(player_id).strip(), amount)
            logging.info(f"Postback Recorded: Player {player_id} | Deposit: ${amount:.2f}")
            return web.Response(text="OK", status=200)
        
        return web.Response(text="Missing player_id", status=400)
    except Exception as e:
        logging.error(f"Postback error: {e}")
        return web.Response(text="Error", status=500)

# --- BOT TELEGRAM HANDLERS ---
def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "en")

def build_main_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    keyboard = [
        [InlineKeyboardButton(t["btn_reg_link"], url=AFFILIATE_LINK)],
        [InlineKeyboardButton(t["btn_step1"], callback_data="verify_reg")],
        [InlineKeyboardButton(t["btn_step2"], callback_data="verify_dep")],
        [InlineKeyboardButton(t["btn_lang"], callback_data="toggle_language")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    t = TEXTS[lang]
    welcome_text = t["welcome"].format(promo=PROMO_CODE, min_dep=MIN_DEPOSIT_USD)
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=build_main_keyboard(lang))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_lang(context)
    t = TEXTS[lang]

    if query.data == "toggle_language":
        new_lang = "fr" if lang == "en" else "en"
        context.user_data["lang"] = new_lang
        t_new = TEXTS[new_lang]
        welcome_text = t_new["welcome"].format(promo=PROMO_CODE, min_dep=MIN_DEPOSIT_USD)
        await query.message.reply_text(t_new["lang_selected"], parse_mode="Markdown")
        await query.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=build_main_keyboard(new_lang))

    elif query.data == "verify_reg":
        await query.message.reply_text(t["prompt_id"], parse_mode="Markdown")
        context.user_data["awaiting_account_id"] = True

    elif query.data == "verify_dep":
        account_id = context.user_data.get("saved_account_id")
        if not account_id:
            await query.message.reply_text(t["no_id_saved"], parse_mode="Markdown")
            return

        deposit_amount, invite_claimed = check_deposit_status(account_id)

        if invite_claimed == 1:
            msg = t["already_issued"].format(id=account_id)
            await query.message.reply_text(msg, parse_mode="Markdown")
            return

        if deposit_amount >= MIN_DEPOSIT_USD:
            expiring_link = await generate_expiring_invite_link(context.bot, query.from_user.id)
            mark_invite_as_issued(account_id)
            
            keyboard = [[InlineKeyboardButton(t["btn_join"], url=expiring_link)]]
            msg = t["dep_success"].format(amount=deposit_amount, mins=LINK_EXPIRE_MINUTES)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            keyboard = [[InlineKeyboardButton(t["btn_recheck"], callback_data="verify_dep")]]
            msg = t["dep_pending"].format(id=account_id, min_dep=MIN_DEPOSIT_USD, amount=deposit_amount)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_account_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    lang = get_lang(context)
    t = TEXTS[lang]

    if user_data.get("awaiting_account_id"):
        user_account_id = update.message.text.strip()
        user_data["awaiting_account_id"] = False

        await update.message.reply_text(t["verifying_db"])
        claim_status = attempt_claim_account(user_account_id, update.effective_user.id)

        if claim_status in ["success", "already_owned"]:
            user_data["saved_account_id"] = user_account_id
            keyboard = [[InlineKeyboardButton(t["btn_step2"], callback_data="verify_dep")]]
            msg = t["reg_success"].format(id=user_account_id, min_dep=MIN_DEPOSIT_USD)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif claim_status == "claimed_by_other":
            keyboard = [[InlineKeyboardButton(t["btn_retry_id"], callback_data="verify_reg")]]
            msg = t["already_claimed_other"].format(id=user_account_id)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        
        else:  # not_found
            keyboard = [
                [InlineKeyboardButton(t["btn_reg_link"], url=AFFILIATE_LINK)],
                [InlineKeyboardButton(t["btn_retry_id"], callback_data="verify_reg")]
            ]
            msg = t["reg_failed"].format(id=user_account_id, promo=PROMO_CODE)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- APPLICATION RUNNER ---
async def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(verify_reg|verify_dep|toggle_language)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_id))

    web_app = web.Application()
    web_app.router.add_route("*", "/postback", handle_1win_postback)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    logging.info(f"S2S Webhook server running on port {WEBHOOK_PORT}")

    async with app:
        await app.start()
        await app.updater.start_polling()
        logging.info("Telegram Bot actively listening for messages...")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
