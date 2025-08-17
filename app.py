# app.py
import os, re, json, requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

# ──────────────────────────────────────────────────────────────────────────────
# ENV
# ──────────────────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SabinaSecret")

BASE_URL       = os.getenv("BASE_URL", "https://sabina-energy-hd-bot.onrender.com")
FREE_CALC_URL  = os.getenv("FREE_CALC_URL",  "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")
PAID_CALC_URL  = os.getenv("PAID_CALC_URL",  "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")
VIDEO_URL      = os.getenv("VIDEO_URL",      "https://t.me/your_channel/123")

# Веб-хук для записи лида в Google Sheets (Apps Script или форма) – см. инструкцию ниже.
LEAD_WEBHOOK_URL = os.getenv("LEAD_WEBHOOK_URL", "")  # оставь пустым, если пока не настроено

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ──────────────────────────────────────────────────────────────────────────────
# Flask
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="webapp", static_url_path="/hd")

# Папка с медиакарточками (положи файлы в ./static/cards/)
CARDS_DIR = "static/cards"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def tg(method: str, **params):
    try:
        r = requests.post(f"{TG_API}/{method}", json=params, timeout=15)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def reply_kb(rows):
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}

def inline_btn(text, url=None, data=None):
    b = {"text": text}
    if url:  b["url"] = url
    if data: b["callback_data"] = data
    return b

def send_photo_if_exists(chat_id: int, filename: str, caption: str = None):
    """
    Отправляет фото, если файл существует в ./static/cards/, иначе ничего.
    Названия файлов ты создаёшь сама (см. TYPE_CARD / PROFILE_CARD ниже).
    """
    path = os.path.join(CARDS_DIR, filename)
    if os.path.exists(path):
        # Telegram принимает URL, поэтому отдадим через наш сервер
        photo_url = f"{BASE_URL}/cards/{filename}"
        tg("sendPhoto", chat_id=chat_id, photo=photo_url, caption=caption, parse_mode="HTML")

def email_valid(s: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", s.strip()))

# ──────────────────────────────────────────────────────────────────────────────
# Контент
# ──────────────────────────────────────────────────────────────────────────────
ABOUT_HD = [
    "✨ <b>Human Design</b> — система про жизнь в согласии со своей природой.",
    "🔭 Синтез астрологии, И-Цзин, Каббалы, чакровой модели и идеи о нейтрино.",
    "🎯 Ключ: <b>следуй Стратегии и Авторитету</b> — так уходит лишнее напряжение и приходят «свои» возможности."
]

ABOUT_TYPES_SHORT = [
    "📚 <b>Типы (5)</b>:",
    "• Манифестор — инициирует. <i>Стратегия: информировать</i>.",
    "• Генератор — действует из отклика. <i>Стратегия: ждать отклика</i>.",
    "• Маниф. Генератор — быстро тестирует. <i>Стратегия: ждать отклика → информировать</i>.",
    "• Проектор — направляет. <i>Стратегия: ждать приглашения</i>.",
    "• Рефлектор — зеркалит среду. <i>Стратегия: лунный цикл</i>."
]

ABOUT_TYPES_LONG = [
    "⚡️ <b>Манифестор</b>: пришёл инициировать и запускать. Важно информировать близких — тогда энергия течёт свободно.",
    "🔋 <b>Генератор</b>: стабильная жизненная энергия для того, что откликается. Сакральное «угу/неа» — твой навигатор.",
    "🚀 <b>Манифестирующий Генератор</b>: скоростной генератор, любит оптимизировать. Ждёт отклик, затем информирует.",
    "🎯 <b>Проектор</b>: видит людей и системы. Сила раскрывается через признание и корректные приглашения.",
    "🌙 <b>Рефлектор</b>: чувствителен к среде; качество жизни = качество окружения. Важные решения — после лунного цикла."
]

ABOUT_PROFILES_SHORT = [
    "📖 <b>Профили (12)</b>: 1/3, 1/4, 2/4, 2/5, 3/5, 3/6, 4/6, 4/1, 5/1, 5/2, 6/2, 6/3."
]

PROFILE_LONG = {
    "1/3": "1/3 Исследователь-Мученик — фундамент знаний + обучение через личные пробы и ошибки. Стабильность рождается из опыта.",
    "1/4": "1/4 Исследователь-Оппортунист — прочная база + сила отношений. Влияешь через близкий круг.",
    "2/4": "2/4 Отшельник-Оппортунист — талант в уединении, возможности из окружения. Важно и отдыхать, и быть на виду.",
    "2/5": "2/5 Отшельник-Еретик — практичные решения для других, при этом нужна «берлога» для восстановления.",
    "3/5": "3/5 Мученик-Еретик — экспериментатор-спасатель. Через попытки находишь рабочие пути для себя и людей.",
    "3/6": "3/6 Мученик-Ролевая модель — сначала жизненные приключения, потом мудрое созерцание и пример для других.",
    "4/6": "4/6 Оппортунист-Ролевая модель — опора на связи + зрелая мудрость с возрастом. Не спеши — всё вовремя.",
    "4/1": "4/1 Оппортунист-Исследователь — редкий баланс связей и фундамента. Важно держать свой курс.",
    "5/1": "5/1 Еретик-Исследователь — видишь проблемы и решаешь их. Проверяй ожидания людей, сохраняй границы.",
    "5/2": "5/2 Еретик-Отшельник — тебя зовут на «пожар», а силы рождаются в уединении. Балансируй внешний запрос и отдых.",
    "6/2": "6/2 Ролевая модель-Отшельник — три этапа жизни: опыт, наблюдение, пример. Тишина — твой ресурс.",
    "6/3": "6/3 Ролевая модель-Мученик — мудрость через проживание. Гибкость и чувство юмора — лучшие спутники."
}

TYPE_MINI = {
    "манифестор": "⚡️ <b>Манифестор</b>: инициируй и информируй — так сила течёт мягче.",
    "генератор": "🔋 <b>Генератор</b>: следуй сакральному отклику. То, что «да», наполняет энергией.",
    "манифестирующий генератор": "🚀 <b>Манифестирующий генератор</b>: сначала отклик, затем информирование. Быстро тестируй и оптимизируй.",
    "проектор": "🎯 <b>Проектор</b>: ищи признание и корректные приглашения — здесь раскрывается твоя глубина.",
    "рефлектор": "🌙 <b>Рефлектор</b>: выбирай среду и людей — это ключ. Важные решения — по лунному циклу."
}

PROFILE_MINI = {
    "1/3": "1/3: фундамент + опыт через «пробовал-узнал».",
    "1/4": "1/4: знания + влияние через круг общения.",
    "2/4": "2/4: талант в уединении, зовёт окружение.",
    "2/5": "2/5: практичность для других, береги ресурс.",
    "3/5": "3/5: находишь рабочие решения через опыт.",
    "3/6": "3/6: путь к мудрости через проживание этапов.",
    "4/6": "4/6: сила в связях и зрелости.",
    "4/1": "4/1: редкий баланс связей и фундамента.",
    "5/1": "5/1: стратег, проверяй ожидания других.",
    "5/2": "5/2: востребованность + необходимость уединения.",
    "6/2": "6/2: пример для других, ресурс — тишина.",
    "6/3": "6/3: мудрость через приключения и гибкость."
}

# Для карточек: названия файлов, которые ты положишь в ./static/cards/
TYPE_CARD = {
    "манифестор": "type_manifestor.jpg",
    "генератор": "type_generator.jpg",
    "манифестирующий генератор": "type_mg.jpg",
    "проектор": "type_projector.jpg",
    "рефлектор": "type_reflector.jpg",
}

PROFILE_CARD = {
    k: f"profile_{k.replace('/','-')}.jpg" for k in PROFILE_MINI.keys()
}

# ──────────────────────────────────────────────────────────────────────────────
# Меню
# ──────────────────────────────────────────────────────────────────────────────
MAIN_KB = reply_kb([
    ["✨ Рассчитать бодиграф", "💎 Платный расчёт"],
    ["🎬 Видео / инструкция"],
    ["ℹ️ Что такое Human Design?"],
    ["📚 О типах", "📖 О профилях"],
    ["📝 Я знаю свой тип/профиль"],
    ["💼 Мои услуги", "🎁 Подарок / гайд"]
])

# Состояния
USER_STATE = {}   # chat_id -> "await_type_profile" | "await_email" | None

# ──────────────────────────────────────────────────────────────────────────────
# Веб-часть
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return "OK"

@app.get("/hd")
def webapp_index():
    return send_from_directory("webapp", "index.html")

@app.get("/hd/<path:fname>")
def webapp_files(fname):
    return send_from_directory("webapp", fname)

@app.get("/privacy")
def privacy():
    return send_from_directory("static", "privacy.html")

# Раздача медиакарточек
@app.get("/cards/<path:fname>")
def cards(fname):
    return send_from_directory(CARDS_DIR, fname)

# Удобно установить вебхук из браузера
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
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()

    if not chat_id:
        return "ok"

    # /start
    if text.startswith("/start"):
        intro = (
            "Привет! Это бот <b>Sabina Energy</b> по Human Design.\n\n"
            "• сделай <b>бесплатный расчёт</b>\n"
            "• узнай основы\n"
            "• перейди к <b>платному отчёту</b>\n"
            "• посмотри видео\n\n"
            "Когда рассчитаешь карту — вернись и напиши сюда свой <b>тип</b> и <b>профиль</b> (например, «эмоциональный генератор 3/5»). Я пришлю мини-разбор ✨"
        )
        tg("sendMessage", chat_id=chat_id, text=intro, parse_mode="HTML", reply_markup=MAIN_KB)
        USER_STATE.pop(chat_id, None)
        return "ok"

    # Кнопки
    if text == "✨ Рассчитать бодиграф":
        caption = (
            "Открой калькулятор и заполни данные.\n"
            "Когда увидишь свой <b>тип</b> и <b>профиль</b> — вернись и напиши их сюда, я пришлю мини-разбор ✨"
        )
        tg("sendMessage", chat_id=chat_id, text=caption, parse_mode="HTML",
           reply_markup={"inline_keyboard":[[inline_btn("Открыть калькулятор", url=FREE_CALC_URL)]]})
        return "ok"

    if text == "💎 Платный расчёт":
        tg("sendMessage", chat_id=chat_id, text="Подробный электронный отчёт:", parse_mode="HTML",
           reply_markup={"inline_keyboard":[[inline_btn("Перейти к платному расчёту", url=PAID_CALC_URL)]]})
        return "ok"

    if text == "🎬 Видео / инструкция":
        tg("sendMessage", chat_id=chat_id, text="Как пользоваться ботом:", parse_mode="HTML",
           reply_markup={"inline_keyboard":[[inline_btn("Смотреть видео", url=VIDEO_URL)]]})
        return "ok"

    if text == "ℹ️ Что такое Human Design?":
        for p in ABOUT_HD: tg("sendMessage", chat_id=chat_id, text=p, parse_mode="HTML")
        return "ok"

    if text == "📚 О типах":
        for p in ABOUT_TYPES_SHORT: tg("sendMessage", chat_id=chat_id, text=p, parse_mode="HTML")
        # длинная шпаргалка
        for p in ABOUT_TYPES_LONG: tg("sendMessage", chat_id=chat_id, text=p, parse_mode="HTML")
        return "ok"

    if text == "📖 О профилях":
        for p in ABOUT_PROFILES_SHORT: tg("sendMessage", chat_id=chat_id, text=p, parse_mode="HTML")
        for key in ["1/3","1/4","2/4","2/5","3/5","3/6","4/6","4/1","5/1","5/2","6/2","6/3"]:
            tg("sendMessage", chat_id=chat_id, text=f"• <b>{key}</b> — {PROFILE_LONG[key]}", parse_mode="HTML")
        return "ok"

    if text == "💼 Мои услуги":
        services = (
            "💼 <b>Мои услуги</b>\n\n"
            "• Индивидуальная консультация 90 минут + отчёт.\n"
            "• Разбор типа, стратегии, авторитета и профиля.\n\n"
            "Напишите мне в личные сообщения:"
        )
        tg("sendMessage", chat_id=chat_id, text=services, parse_mode="HTML",
           reply_markup={"inline_keyboard":[[inline_btn("Написать Сабине", url="https://t.me/coachsabina")]]})
        return "ok"

    if text == "🎁 Подарок / гайд":
        USER_STATE[chat_id] = "await_email"
        ask = "Оставь e-mail — пришлю мини-гайд на почту ✉️"
        tg("sendMessage", chat_id=chat_id, text=ask)
        return "ok"

    if text == "📝 Я знаю свой тип/профиль":
        USER_STATE[chat_id] = "await_type_profile"
        tg("sendMessage", chat_id=chat_id,
           text="Напиши свой <b>тип</b> и <b>профиль</b> в одном сообщении (например: «эмоциональный генератор 3/5»).",
           parse_mode="HTML")
        return "ok"

    # Сбор e-mail
    if USER_STATE.get(chat_id) == "await_email":
        if email_valid(text):
            save_lead(chat_id=chat_id, email=text, source="gift")
            USER_STATE[chat_id] = None
            tg("sendMessage", chat_id=chat_id, text="Спасибо! Гайд скоро придёт на почту ✨", reply_markup=MAIN_KB)
        else:
            tg("sendMessage", chat_id=chat_id, text="Хмм… это не похоже на e-mail. Пришли адрес вида name@mail.com")
        return "ok"

    # Мини-разбор по типу/профилю
    if USER_STATE.get(chat_id) == "await_type_profile" or text:
        if handle_free_text(chat_id, text):
            USER_STATE[chat_id] = None
            return "ok"

    tg("sendMessage", chat_id=chat_id, text="Выбери действие из меню 👇", reply_markup=MAIN_KB)
    return "ok"

# ──────────────────────────────────────────────────────────────────────────────
# Разбор свободного текста: тип/профиль и «эмоциональный/селезёночный/сакральный»
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
    cleaned = text.lower().replace(" ", "")
    m = PROFILE_REGEX.search(cleaned)
    if not m:
        return None
    prof = m.group(1).replace(".", "/")
    return prof if prof in PROFILE_MINI else None

def detect_authority_suffix(text: str):
    s = text.lower()
    if "эмоци" in s:     return " (эмоциональный)"
    if "селез" in s:     return " (селезёночный)"
    if "сакрал" in s:    return " (сакральный)"
    return ""

def handle_free_text(chat_id, text):
    if not text:
        return False

    detected_type = detect_type(text)
    detected_profile = detect_profile(text)
    authority = detect_authority_suffix(text)

    # ничего не распознали — не перехватываем
    if not detected_type and not detected_profile:
        return False

    parts = []

    if detected_type:
        base = TYPE_MINI.get(detected_type, "")
        if base:
            # добавляем «эмоциональный/селезёночный/сакральный» прямо в жирный заголовок
            base = base.replace("</b>:", f"</b>{authority}:")
            parts.append(base)
            # попробуем отправить карточку типа
            send_photo_if_exists(chat_id, TYPE_CARD.get(detected_type, ""))

    if detected_profile:
        parts.append("🧩 " + PROFILE_MINI[detected_profile])
        # карточка профиля, если есть
        send_photo_if_exists(chat_id, PROFILE_CARD.get(detected_profile, ""))

    text_out = "\n\n".join(parts) + "\n\nЕсли хочешь глубже — жми «💎 Платный расчёт» или напиши мне в личку."
    tg("sendMessage", chat_id=chat_id, text=text_out, parse_mode="HTML", reply_markup=MAIN_KB)

    # Сохраним лид (если подключён веб-хук)
    save_lead(chat_id=chat_id, user_text=text, hd_type=detected_type, profile=detected_profile, tag="type_profile")

    return True

# ──────────────────────────────────────────────────────────────────────────────
# Сохранение лида в Google Sheets (через Apps Script / форму)
# ──────────────────────────────────────────────────────────────────────────────
def save_lead(chat_id: int, email: str = None, user_text: str = None,
              hd_type: str = None, profile: str = None, source: str = None, tag: str = None):
    if not LEAD_WEBHOOK_URL:
        return
    payload = {
        "chat_id": chat_id,
        "username": None,
        "email": email,
        "text": user_text,
        "type": hd_type,
        "profile": profile,
        "source": source,
        "tag": tag,
        "ts": datetime.utcnow().isoformat()
    }
    try:
        requests.post(LEAD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception:
        pass

# ──────────────────────────────────────────────────────────────────────────────
# Gunicorn entry
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

app = app
