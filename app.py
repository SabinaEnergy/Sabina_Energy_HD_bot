import os, re, time, json, requests
from flask import Flask, request, jsonify
import telebot
from telebot import types

# ========= ENV =========
BOT_TOKEN    = os.getenv("BOT_TOKEN", "").strip()
BASE_URL     = os.getenv("BASE_URL", "https://example.onrender.com").rstrip("/")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SabinaSecret2025")

# куда ведём на бесплатный/платный расчёт (твоя реф-ссылка)
FREE_CALC_URL = os.getenv(
    "FREE_CALC_URL",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/?rave=7366406054640513"
)
PAID_CALC_URL = os.getenv(
    "PAID_CALC_URL",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/?rave=7366406054640513"
)
VIDEO_URL    = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
SERVICES_URL = os.getenv("SERVICES_URL", "https://t.me/your_contact")  # куда писать/записаться

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ========= APP/TELEBOT =========
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ========= ТЕКСТЫ (твои материалы) =========
TEXT_INTRO = (
    "✨ *Что такое Human Design?*\n"
    "Human Design появился в 1987 году после мистического опыта Ра Уру Ху на Ибице.\n"
    "Это синтез астрологии, И-Цзин, Каббалы, чакровой системы и идей квантовой физики.\n"
    "Главная цель — жить в согласии со своей природой, вместо борьбы с собственной механикой."
)

TEXT_NEUTRINO = (
    "🌌 *Концепция нейтрино*\n"
    "Нейтрино — микрочастицы, проходящие через всё. Поток несёт «отпечаток» планет в момент рождения.\n"
    "Этот отпечаток фиксируется в бодиграфе и формирует уникальный набор энергий."
)

TEXT_CENTERS = (
    "🔹 *9 центров бодиграфа*\n"
    "1) Корневой — давление действовать, стресс.\n"
    "2) Сакральный — жизненная энергия, отклик, удовольствие.\n"
    "3) Селезёночный — интуиция, здоровье, выживание.\n"
    "4) Солнечное сплетение — эмоции, волны.\n"
    "5) Сердечный (Эго) — воля, сила, желания.\n"
    "6) Горловой — коммуникация, проявление.\n"
    "7) Аджна — анализ, концепции.\n"
    "8) Теменной — вдохновение, вопросы.\n"
    "9) G-центр — любовь, направление, идентичность.\n\n"
    "Определённые центры = стабильная энергия.\n"
    "Неопределённые = чувствительность к окружению."
)

TEXT_TYPES_STRATEGY = (
    "🧠 *Типы и стратегии*\n"
    "• *Манифестор* — инициирует. Стратегия: *информировать* перед действиями.\n"
    "• *Генератор* — создаёт и реализует. Стратегия: *ждать отклика*.\n"
    "• *Манифестирующий генератор* — скорость Манифестора + устойчивость Генератора. "
    "Стратегия: *ждать отклика*, затем *информировать*.\n"
    "• *Проектор* — направляет других. Стратегия: *ждать приглашения*.\n"
    "• *Рефлектор* — зеркалит окружение. Стратегия: *ждать лунный цикл (≈28 дней)*."
)

TEXT_AUTHORITIES = (
    "🧭 *Авторитеты (как принимать решения)*\n"
    "• *Эмоциональный* — решение после прожитой волны.\n"
    "• *Сакральный* — мгновенный отклик тела.\n"
    "• *Селезёночный* — тихая интуиция «здесь и сейчас».\n"
    "• *Эго (Сердечный)* — через личные желания и обещания себе.\n"
    "• *G-центр* — ощущение направления/идентичности.\n"
    "• *Ментальный (для Проекторов)* — через обсуждение.\n"
    "• *Лунный (для Рефлекторов)* — через цикл Луны."
)

TEXT_PRACTICE = (
    "💡 *Практика*\n"
    "Human Design — не про «исправить себя», а про снять чужие ожидания.\n"
    "Ключ — следовать *Стратегии* и *Авторитету*.\n"
    "Принимая свою механику, мы экономим энергию и притягиваем правильные обстоятельства."
)

TEXT_LISTS = (
    "📚 *Типы в Human Design*\n"
    "1. Манифестор\n2. Генератор\n3. Манифестирующий генератор\n4. Проектор\n5. Рефлектор\n\n"
    "📑 *Профили (12)*\n"
    "1/3, 1/4, 2/4, 2/5, 3/5, 3/6, 4/6, 4/1, 5/1, 5/2, 6/2, 6/3"
)

# ===== ТИПЫ/ПРОФИЛИ — мини-тезисы для авто-разбора =====
TYPE_TIPS = {
    "Генератор": "⚡ Генератор: жди отклика тела. Делай то, что зажигает — энергия придёт.",
    "Манифестирующий генератор": "⚡ МГ: быстрый старт + отклик. Менять курс по ходу — нормально.",
    "Манифестор": "⚡ Манифестор: инициируй и информируй вовлечённых — так меньше сопротивления.",
    "Проектор": "⚡ Проектор: жди признания и приглашения. Фокус на своей экспертизе.",
    "Рефлектор": "⚡ Рефлектор: решения не спеши — наблюдай лунный цикл.",
}

PROFILE_TIPS = {
    "1/3": "🧭 1/3 Исследователь-Экспериментатор: фундамент + обучение на опыте.",
    "1/4": "🧭 1/4 Исследователь-Оппортунист: опора + связи/люди.",
    "2/4": "🧭 2/4 Отшельник-Оппортунист: талант + возможности через людей.",
    "2/5": "🧭 2/5 Отшельник-Еретик: талант + практичность, береги границы ожиданий.",
    "3/5": "🧭 3/5 Экспериментатор-Еретик: пробуй — делай выводы — веди.",
    "3/6": "🧭 3/6 Экспериментатор-Ролевая модель: три этапа жизни → мудрость.",
    "4/1": "🧭 4/1 Оппортунист-Исследователь: устойчивость + важны контакты.",
    "4/6": "🧭 4/6 Оппортунист-Ролевая модель: люди + этапность пути.",
    "5/1": "🧭 5/1 Еретик-Исследователь: практичные решения + опора на фундамент.",
    "5/2": "🧭 5/2 Еретик-Отшельник: спасатель с талантом, береги энергию.",
    "6/2": "🧭 6/2 Ролевая модель-Отшельник: стабильный пример с возрастом.",
    "6/3": "🧭 6/3 Ролевая модель-Экспериментатор: мудрость + живой опыт.",
}

# ===== парсинг типа/профиля из текста =====
TYPE_ALIASES = {
    r"\bманифестир(ующ|ующий)\s*генератор\b": "Манифестирующий генератор",
    r"\bмг\b": "Манифестирующий генератор",
    r"\bгенератор\b": "Генератор",
    r"\bэмоциональн(ый|ая)\s*генератор\b": "Генератор",
    r"\bманифестор\b": "Манифестор",
    r"\bпроектор\b": "Проектор",
    r"\bрефлектор\b": "Рефлектор",
}
PROFILE_RE = re.compile(r"(\b[1-6])\s*[/\.]\s*([1-6]\b)")

def extract_type_and_profile(text: str):
    text_lc = text.lower()
    prof = None
    m = PROFILE_RE.search(text_lc)
    if m: prof = f"{m.group(1)}/{m.group(2)}"
    t = None
    for pat, norm in TYPE_ALIASES.items():
        if re.search(pat, text_lc): t = norm; break
    return t, prof

# ========= КЛАВИАТУРЫ =========
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 Рассчитать бодиграф", "📖 О Human Design")
    kb.row("💼 Мои услуги", "✍️ Я знаю свой тип/профиль")
    return kb

def about_inline():
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("История и происхождение", callback_data="about_history"))
    kb.row(types.InlineKeyboardButton("Концепция нейтрино", callback_data="about_neutrino"))
    kb.row(types.InlineKeyboardButton("9 центров бодиграфа", callback_data="about_centers"))
    kb.row(types.InlineKeyboardButton("Типы и стратегии", callback_data="about_types_strategy"))
    kb.row(types.InlineKeyboardButton("Авторитеты", callback_data="about_authorities"))
    kb.row(types.InlineKeyboardButton("Практика применения", callback_data="about_practice"))
    kb.row(types.InlineKeyboardButton("Список типов и профилей", callback_data="about_lists"))
    return kb

def services_inline():
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("Записаться / задать вопрос", url=SERVICES_URL))
    kb.row(types.InlineKeyboardButton("Платный расчёт на сайте", url=PAID_CALC_URL))
    return kb

# ========= ХЭНДЛЕРЫ =========
@bot.message_handler(commands=["start", "menu"])
def cmd_start(m: types.Message):
    bot.send_message(
        m.chat.id,
        "Привет! Это бот *Sabina Energy* по Human Design.\n\n"
        "Здесь можно: сделать бесплатный расчёт, узнать основы, перейти к платному отчёту и посмотреть мои услуги.",
        reply_markup=main_menu()
    )
    bot.send_message(
        m.chat.id,
        "Если знаешь свой *тип* и *профиль*, просто напиши их сюда (например: _Генератор 3/5_).",
    )

@bot.message_handler(func=lambda ms: ms.text == "📊 Рассчитать бодиграф")
def on_calc(ms: types.Message):
    bot.send_message(
        ms.chat.id,
        "🔮 Переход на страницу расчёта:\n"
        f"{FREE_CALC_URL}\n\n"
        "На сайте нажми *«Построить карту»*. Когда увидишь свой *тип* и *профиль* — пришли их сюда, я дам мини-разбор.",
        disable_web_page_preview=False
    )

@bot.message_handler(func=lambda ms: ms.text == "📖 О Human Design")
def on_about(ms: types.Message):
    bot.send_message(ms.chat.id, "Выбирай раздел 👇", reply_markup=about_inline())

@bot.message_handler(func=lambda ms: ms.text == "💼 Мои услуги")
def on_services(ms: types.Message):
    bot.send_message(
        ms.chat.id,
        "💼 *Мои услуги*\n"
        "— Индивидуальный разбор HD\n"
        "— Совместимость (пары/дети)\n"
        "— Бизнес по Дизайну\n"
        "— Наставничество\n\n"
        "Нажми кнопку ниже, чтобы записаться или задать вопрос.",
        reply_markup=services_inline()
    )

@bot.message_handler(func=lambda ms: ms.text == "✍️ Я знаю свой тип/профиль")
def on_iknow(ms: types.Message):
    bot.send_message(
        ms.chat.id,
        "Отправь свой *тип* и *профиль* одним сообщением.\n"
        "Примеры: _Манифестирующий генератор 3/5_, _Проектор 4.1_, _Генератор 2/4_."
    )

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("about_"))
def on_about_cb(c: types.CallbackQuery):
    data = c.data
    mapping = {
        "about_history": TEXT_INTRO,
        "about_neutrino": TEXT_NEUTRINO,
        "about_centers": TEXT_CENTERS,
        "about_types_strategy": TEXT_TYPES_STRATEGY,
        "about_authorities": TEXT_AUTHORITIES,
        "about_practice": TEXT_PRACTICE,
        "about_lists": TEXT_LISTS,
    }
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, mapping.get(data, "Раздел в разработке."))

@bot.message_handler(content_types=["text"])
def on_text(ms: types.Message):
    # пытаемся распознать тип/профиль из свободного текста
    t, prof = extract_type_and_profile(ms.text or "")
    if not t and not prof:
        # не поняли — напомним меню и формат
        bot.send_message(
            ms.chat.id,
            "Не совсем поняла 🤔\n"
            "Отправь свой *тип* и *профиль* одной строкой.\n"
            "Примеры: _Манифестирующий генератор 3/5_, _Проектор 4.1_, _Генератор 2/4_.",
            reply_markup=main_menu()
        )
        return

    parts = []
    if t:
        parts.append(f"Тип: *{t}*\n{TYPE_TIPS.get(t,'Твой тип — твоя стратегия взаимодействия.')}")
    if prof:
        parts.append(f"Профиль: *{prof}*\n{PROFILE_TIPS.get(prof,'Профиль — про роли и способ обучения.')}")

    final = "✅ Твоё краткое резюме:\n\n" + "\n\n".join(parts)
    bot.send_message(
        ms.chat.id,
        final,
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("💎 Платный расчёт", url=PAID_CALC_URL),
        )
    )

# ========= ВЕБХУКИ/ФЛАСК =========
@app.get("/")
def health():
    return "OK"

@app.get("/set-webhook")
def set_webhook():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is empty"})
    url = f"{BASE_URL}/tg/webhook"
    r = requests.get(
        f"{TG_API}/setWebhook",
        params={"url": url, "secret_token": SECRET_TOKEN},
        timeout=15
    )
    try:
        return jsonify(r.json())
    except Exception:
        return r.text, r.status_code

@app.get("/get-webhook-info")
def get_webhook_info():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is empty"})
    r = requests.get(f"{TG_API}/getWebhookInfo", timeout=15)
    try:
        return jsonify(r.json())
    except Exception:
        return r.text, r.status_code

@app.post("/tg/webhook")
def tg_webhook():
    # проверим секрет
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403
    try:
        update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
    except Exception:
        # чтобы вебхук не падал
        pass
    return "ok"

# ========= ЛОКАЛЬНЫЙ ЗАПУСК =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
