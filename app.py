import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# === ЛОГИ ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === Состояния анкеты ===
ASK_DATE, ASK_TIME, ASK_PLACE = range(3)

# === СТАРТ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["✨ Рассчитать бодиграф бесплатно"],
        ["ℹ️ Что такое Human Design?"],
        ["🎥 Посмотреть видео"],
        ["💜 Платный расчёт"]
    ]
    await update.message.reply_text(
        "Привет 🌸 Я — твой проводник в Human Design.\n\n"
        "Жми кнопку ниже, чтобы рассчитать свой бодиграф или узнать подробнее:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# === АНКЕТА ===
async def free_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✨ Отлично! Давай начнём.\n\nВведи свою дату рождения (в формате: 22.10.1985):")
    return ASK_DATE

async def ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["birth_date"] = update.message.text
    await update.message.reply_text("⏰ Теперь укажи время рождения (например: 15:03).\n"
                                    "Если не знаешь точно — напиши 'утро', 'день' или 'вечер'.")
    return ASK_TIME

async def ask_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["birth_time"] = update.message.text
    await update.message.reply_text("🌍 И последнее — укажи место рождения (город, страна):")
    return ASK_PLACE

async def finish_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["birth_place"] = update.message.text

    date = context.user_data["birth_date"]
    time = context.user_data["birth_time"]
    place = context.user_data["birth_place"]

    # 🔗 Ссылка на human-design.space (примерно так)
    url = f"https://human-design.space/#/?date={date}&time={time}&place={place}"

    await update.message.reply_text(
        f"🔮 Вот ссылка на твой бодиграф:\n[{date}, {time}, {place}]({url})",
        parse_mode="Markdown"
    )
    await update.message.reply_text("⚡️ Когда увидишь свой тип и профиль — напиши их сюда, и я дам тебе подсказки ✨")

    return ConversationHandler.END

# === ОПИСАНИЯ ===
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Human Design — это система самопознания.\n"
        "В ней есть 5 типов и 12 профилей.\n\n"
        "Хочешь узнать про свой тип и профиль?\nЖми 'Рассчитать бодиграф бесплатно'!"
    )

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎥 Видео о том, как пользоваться ботом: [смотреть](https://t.me/твоя_ссылка)", parse_mode="Markdown")

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 Для расширенного расчёта переходи по ссылке:\n"
        "[Сделать платный расчёт](https://human-design.space/dizajn-cheloveka-raschet-karty/#/)",
        parse_mode="Markdown"
    )

# === ОСНОВНОЙ ХЭНДЛЕР ===
def main():
    # 🔑 ВСТАВЬ свой токен
    TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("✨ Рассчитать бодиграф бесплатно"), free_calc)],
        states={
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_time)],
            ASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_place)],
            ASK_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_calc)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex("ℹ️ Что такое Human Design?"), about))
    app.add_handler(MessageHandler(filters.Regex("🎥 Посмотреть видео"), video))
    app.add_handler(MessageHandler(filters.Regex("💜 Платный расчёт"), paid))

    print("Бот запущен 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
