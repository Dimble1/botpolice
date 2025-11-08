import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Получение токена из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

KEYWORDS = ["18+", "гадание", "предсказание", "будущее"]

async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg and msg.chat.type in ['group', 'supergroup']:
        text = msg.text or ''
        if any(word.lower() in text.lower() for word in KEYWORDS):
            try:
                await msg.delete()
                await msg.reply_text(
                    f"🚫 @{msg.from_user.username}, сообщение удалено. В этой группе запрещён контент 18+ и гадания/предсказания."
                )
            except Exception as e:
                print(f"Ошибка при удалении: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), filter_messages))
    print("Бот запущен через long polling")
    app.run_polling()
