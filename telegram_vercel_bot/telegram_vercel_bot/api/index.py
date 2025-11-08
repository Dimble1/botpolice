import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BOT_TOKEN must be provided via Environment Variables (Vercel -> Settings -> Environment Variables)
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Add BOT_TOKEN to environment variables (do NOT put it in the code).")

# --- Filters (edit to add/remove phrases) ---
RE_18PLUS = re.compile(r"\b(18\+|18\s*\+|18лет|18\s*лет|только\s*для\s*взрослых|взрослым)\b", re.IGNORECASE)
RE_FORTUNE = re.compile(r"\b(гадан(ие|ия)?|гадать|предсказ(ание|ать)|пророче(ство|ствовать)|таро|гороскоп|ясновид(ение|ец)?)\b", re.IGNORECASE)

def is_forbidden(text: str) -> bool:
    if not text:
        return False
    return bool(RE_18PLUS.search(text) or RE_FORTUNE.search(text))

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот активен. Удаляю 18+ и сообщения с гаданиями. Админы не удаляются.")

# --- Message handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    bot = context.bot

    # Only in groups
    if chat.type not in ("group", "supergroup"):
        return

    # Don't act on service messages
    if not msg:
        return

    # Allow admins (skip deletion for chat admins)
    try:
        member = await bot.get_chat_member(chat_id=chat.id, user_id=msg.from_user.id)
        if member.status in ("administrator", "creator"):
            # don't delete admin messages
            return
    except Exception:
        # If we can't fetch member info, proceed cautiously
        pass

    # Get text content (text messages or captions)
    text_to_check = msg.text or msg.caption or ""
    if is_forbidden(text_to_check):
        try:
            # Delete the offending message
            await bot.delete_message(chat_id=chat.id, message_id=msg.message_id)
        except Exception as e:
            logger.warning("Failed to delete message: %s", e)
            return

        # Prepare mention (prefer @username, fallback to first name)
        user = msg.from_user
        if user:
            if user.username:
                mention = f"@{user.username}"
            else:
                # Use first name and escape if necessary
                name = user.first_name or "пользователь"
                mention = name
        else:
            mention = "пользователь"

        # Send a warning message mentioning the user (reply to nothing to avoid spam)
        warn_text = f"🚫 {mention}, сообщение удалено. В этой группе запрещён контент 18+ и гадания/предсказания."
        try:
            await bot.send_message(chat_id=chat.id, text=warn_text)
        except Exception as e:
            logger.warning("Failed to send warning message: %s", e)

# --- App initialization ---
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

# --- Vercel handler ---
# Vercel will call this function for incoming HTTP requests.
async def handler(request):
    # Accept health check
    if request.method == "GET":
        return {"statusCode": 200, "body": "Bot is running (webhook endpoint)."}

    # Telegram will POST updates as JSON
    if request.method == "POST":
        data = await request.json()
        update = Update.de_json(data, app.bot)
        # Initialize the app (only the first time; harmless to call multiple times)
        await app.initialize()
        await app.process_update(update)
        return {"statusCode": 200, "body": "ok"}

    return {"statusCode": 405, "body": "Method Not Allowed"}
