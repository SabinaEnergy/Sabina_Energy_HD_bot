# app.py
import os, re, json, requests
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from flask import Flask, request, jsonify, send_from_directory

# ──────────────────────────────────────────────────────────────────────────────
# ENV
# ──────────────────────────────────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
SECRET_TOKEN    = os.getenv("SECRET_TOKEN", "SabinaSecret")

BASE_URL        = os.getenv("BASE_URL", "https://sabina-energy-hd-bot.onrender.com")
FREE_CALC_URL   = os.getenv("FREE_CALC_URL",  "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")
PAID_CALC_URL   = os.getenv("PAID_CALC_URL",  "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")
LEAD_FORM_URL   = os.getenv("LEAD_FORM_URL",  "https://forms.gle/xxxx")
VIDEO_URL       = os.getenv("VIDEO_URL",      "https://t.me/your_channel/123")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ──────────────────────────────────────────────────────────────────────────────
# Flask
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="webapp", static_url_path="/hd")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def tg(method: str, **params):
    """Call Telegram Bot API with json body."""
    try:
        r = requests.post(f"{TG_API}/{method}", json=params, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def reply_kb(button_rows):
    """Reply keyboard (persistent menu)."""
    return {
        "keyboard": button_rows,
        "resize_keyboard": True,
        "is_persistent": True
    }

def inline_btn(text, url=None, data=None):
    b = {"text": text}
    if url:  b["url"] = url
    if data: b["callback_data"] = data
    return b

def format_b(old):
    """Make **bold** words for Telegram via <b>..</b>."""
    return old.replace("**", "<b>").replace("__", "</b>")

# ──────────────────────────────────────────────────────────────────────────────
# Content (краткие тексты, которые ты прислала)
# ──────────────────────────────────────────────────────────────────────────────
ABOUT_HD = [
    "✨ <b>Human Design</b> — система про то, как жить в согласии со своей природой, без борьбы с собой.",
    "🔭 Это синтез астрологии, И-Цзин, Каббалы, чакровой модели и современной науки о нейтрино.",
    "🎯 Главный ключ — <b>следовать Стратегии и Авторитету</b>. Так уходит лишнее напряжение и приходят «свои» возможности."
]

ABOUT_TYPES = [
    "📚 <b>Типы в Human Design</b> (всего 5):",
    "• Манифестор — инициирует. <i>Стратегия: информировать</i>.",
    "• Генератор — создаёт через отклик. <i>Стратегия: ждать отклика</i>.",
    "• Манифестирующий Генератор — быстрый генератор. <i>Стратегия: ждать отклика → информировать</i>.",
    "• Проектор — видит и направляет. <i>Стратегия: ждать приглашения</i>.",
    "• Рефлектор — зеркалит среду. <i>Стратегия: ждать лунный цикл</i>."
]

ABOUT_PROFILES = [
    "📖 <b>Профили</b> — комбинации двух линий. Всего 12:",
    "1/3, 1/4, 2/4, 2/5, 3/5, 3/6, 4/6, 4/1, 5/1, 5/2, 6/2, 6/3."
]

TYPE_MINI = {
    "манифестор": "⚡️ <b>Манифестор</b>: здесь, чтобы инициировать. Сила — в самостоятельных стартах и честном информировании.",
    "генератор": "🔋 <b>Генератор</b>: стабильная энергия на то, что по-настоящему откликается. Слушай сакральный «да/нет».",
    "манифестирующий генератор": "🚀 <b>Манифестирующий генератор</b>: быстро тестируешь и оптимизируешь. Жди отклика, а потом информируй.",
    "проектор": "🎯 <b>Проектор</b>: видишь людей и системы. Сила — в признании и корректных приглашениях.",
    "рефлектор": "🌙 <b>Рефлектор</b>: чувствительность к среде. Важны правильные люди и время; ключевые решения — по лунному циклу."
}

PROFILE_MINI = {
    "1/3": "1/3 Исследователь-Мученик: учишься через эксперименты и личный опыт.",
    "1/4": "1/4 Исследователь-Оппортунист: фундамент + связи, влияние через отношения.",
    "2/4": "2/4 Отшельник-Оппортунист: талант в уединении, возможности приходят от людей.",
    "2/5": "2/5 Отшельник-Еретик: практичные решения для других, важно беречь энергию.",
    "3/5": "3/5 Мученик-Еретик: пробуешь, падаешь, поднимаешься — находишь рабочие решения.",
    "3/6": "3/6 Мученик-Ролевая модель: путь опытом к мудрости, особенно после 30/50.",
    "4/6": "4/6 Оппортунист-Ролевая модель: влияние через круг общения; стабильность с возрастом.",
    "4/1": "4/1 Оппортунист-Исследователь: редкий мост — и связи, и фундамент знаний.",
    "5/1": "5/1 Еретик-Исследователь: стратег-решатель; важно проверять реальность ожиданий.",
    "5/2": "5/2 Еретик-Отшельник: востребованная практичность + необходимость уединения.",
    "6/2": "6/2 Ролевая модель-Отшельник: врождённый пример; три этапа жизни, много созерцания.",
    "6/3": "6/3 Ролевая модель-Мученик: мудрость через приключения; гибкость — суперсила."
}

# ──────────────────────────────────────────────────────────────────────────────
# Меню (reply keyboard)
# ──────────────────────────────────────────────────────────────────────────────
MAIN_KB = reply_kb([
    ["✨ Рассчитать бодиграф", "💎 Платный расчёт"],
    ["🎬 Видео / инструкция"],
    ["ℹ️ Что такое Human Design?"],
    ["📚 О типах", "📖 О профилях"],
    ["📝 Я знаю свой тип/профиль"],
    ["💼 Мои услуги", "🎁 Подарок / гайд"]
])

# Память состояний для простого диалога «пришли тип/профиль»
USER_STATE = {}   # chat_id -> "await_type_profile" | None

# ──────────────────────────────────────────────────────────────────────────────
# Веб-часть
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return "OK"

@app.get("/privacy")
def privacy():
    return send_from_directory("static", "privacy.html")

@app.get("/hd")
def webapp_index():
    return send_from_directory("webapp", "index.html")

@app.get("/hd/<path:fname>")
def webapp_files(fname):
    return send_from_directory("webapp", fname)

# Установка вебхука (удобно дернуть из браузера)
@app.get("/set-webhook")
def set_webhook():
    url = f"{BASE_URL}/tg/webhook"
    r = requests.get(
        f"{TG_API}/setWebhook",
        params={"url": url, "secret_token": SECRET_TOKEN},
        timeout=10
    )
    return jsonify(r.json())

# ──────────────────────────────────────────────────────────────────────────────
# Telegram webhook
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/tg/webhook")
def webhook():
    # Проверка секретного токена Telegram
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()

    if not chat_id:
        return "ok"

    # /start
    if text.startswith("/start"):
        intro = (
            "Привет! Это бот <b>Sabina Energy</b> по Human Design.\n\n"
            "Здесь можно:\n"
            "• сделать <b>бесплатный расчёт</b>,\n"
            "• узнать основы,\n"
            "• перейти к <b>платному отчёту</b>,\n"
            "• посмотреть видео.\n\n"
            "Когда рассчитаешь карту на сайте — вернись сюда и напиши свой <b>тип</b> и <b>профиль</b>. "
            "Я пришлю мини-разбор ✨"
        )
        tg("sendMessage", chat_id=chat_id, text=intro, parse_mode="HTML", reply_markup=MAIN_KB)
        USER_STATE.pop(chat_id, None)
        return "ok"

    # Кнопки главного меню
    if text == "✨ Рассчитать бодиграф":
        caption = (
            "Открой калькулятор и заполни данные.\n"
            "Когда увидишь свой <b>тип</b> и <b>профиль</b> — вернись сюда и напиши их, пришлю мини-разбор ✨"
        )
        tg("sendMessage",
           chat_id=chat_id,
           text=caption,
           parse_mode="HTML",
           reply_markup={"inline_keyboard":[[inline_btn("Открыть калькулятор", url=FREE_CALC_URL)]]})
        USER_STATE[chat_id] = None
        return "ok"

    if text == "💎 Платный расчёт":
        tg("sendMessage",
           chat_id=chat_id,
           text="Подробный электронный отчёт без моего участия:",
           reply_markup={"inline_keyboard":[[inline_btn("Перейти к платному расчёту", url=PAID_CALC_URL)]]})
        return "ok"

    if text == "🎬 Видео / инструкция":
        tg("sendMessage",
           chat_id=chat_id,
           text="Как пользоваться ботом и где смотреть результаты:",
           reply_markup={"inline_keyboard":[[inline_btn("Смотреть видео", url=VIDEO_URL)]]})
        return "ok"

    if text == "ℹ️ Что такое Human Design?":
        for p in ABOUT_HD: tg("sendMessage", chat_id=chat_id, text=p, parse_mode="HTML")
        return "ok"

    if text == "📚 О типах":
        for p in ABOUT_TYPES: tg("sendMessage", chat_id=chat_id, text=p, parse_mode="HTML")
        return "ok"

    if text == "📖 О профилях":
        for p in ABOUT_PROFILES: tg("sendMessage", chat_id=chat_id, text=p, parse_mode="HTML")
        return "ok"

    if text == "💼 Мои услуги":
        services = (
            "💼 <b>Мои услуги</b>\n\n"
            "• Индивидуальная консультация 90 минут + письменный отчёт.\n"
            "• Разбор типа, стратегии, авторитета и профиля.\n"
            "• Ответы на ваши вопросы.\n\n"
            "Напишите мне в личные сообщения — договоримся о времени:"
        )
        tg("sendMessage", chat_id=chat_id, text=services, parse_mode="HTML",
           reply_markup={"inline_keyboard":[[inline_btn("Написать Сабине", url="https://t.me/coachsabina")]]})
        return "ok"

    if text == "🎁 Подарок / гайд":
        lead = (
            "🎁 Хочешь получить мини-гайд? Оставь e-mail по кнопке ниже, и я пришлю подарок на почту."
        )
        tg("sendMessage", chat_id=chat_id, text=lead,
           reply_markup={"inline_keyboard":[[inline_btn("Оставить e-mail", url=LEAD_FORM_URL)]]})
        return "ok"

    if text == "📝 Я знаю свой тип/профиль":
        prompt = (
            "Отлично! Напиши в одном сообщении свой <b>тип</b> и <b>профиль</b>.\n"
            "Например: <i>эмоциональный генератор 3/5</i> или <i>проектор 4.1</i>."
        )
        USER_STATE[chat_id] = "await_type_profile"
        tg("sendMessage", chat_id=chat_id, text=prompt, parse_mode="HTML")
        return "ok"

    # Если пользователь прислал свободный текст — попробуем распознать тип/профиль
    if USER_STATE.get(chat_id) == "await_type_profile" or text:
        handled = handle_free_text(chat_id, text)
        if handled:
            USER_STATE[chat_id] = None
            return "ok"

    # Если ничего не сработало — покажем меню
    tg("sendMessage", chat_id=chat_id, text="Выбери действие из меню ниже 👇", reply_markup=MAIN_KB)
    return "ok"

# ──────────────────────────────────────────────────────────────────────────────
# Распознавание типа/профиля и мини-разбор
# ──────────────────────────────────────────────────────────────────────────────
TYPE_PATTERNS = [
    ("манифестирующий генератор", ["манифестирующий генератор","мг","маниф. генератор"]),
    ("генератор", ["генератор"]),
    ("манифестор", ["манифестор"]),
    ("проектор", ["проектор"]),
    ("рефлектор", ["рефлектор"]),
]

PROFILE_REGEX = re.compile(r"(\b[1-6][\./][1-6]\b)")

def detect_type(text: str):
    t = text.lower()
    for key, variants in TYPE_PATTERNS:
        for v in variants:
            if v in t:
                return key
    return None

def detect_profile(text: str):
    m = PROFILE_REGEX.search(text.replace(" ", ""))
    if not m:
        return None
    prof = m.group(1).replace(".", "/")
    return prof if prof in PROFILE_MINI else None

def handle_free_text(chat_id, text):
    if not text:
        return False

    t = detect_type(text)
    p = detect_profile(text)

    if not t and not p:
        return False  # не перехватываем — пусть отвечает меню по умолчанию

    parts = []
    if t:
        # улавливаем «эмоциональный/селезёночный/сакральный» и добавляем к типу
        authority_hint = ""
        if "эмоц" in text.lower(): authority_hint = " (эмоциональный)"
        if "селез" in text.lower(): authority_hint = " (селезёночный)"
        if "сакрал" in text.lower(): authority_hint = " (сакральный)"
        parts.append(TYPE_MINI.get(t, "").replace("</b>:", f"</b>{authority_hint}:"))

    if p:
        parts.append("🧩 " + PROFILE_MINI[p])

    if parts:
        msg = "\n\n".join(parts) + "\n\nЕсли хочешь глубже — жми «💎 Платный расчёт» или напиши мне в личку."
        tg("sendMessage", chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=MAIN_KB)
        return True

    return False

# ──────────────────────────────────────────────────────────────────────────────
# Gunicorn entry
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # для локального запуска
    app.run(host="0.0.0.0", port=8000)

# чтобы gunicorn видел объект app
app = app
