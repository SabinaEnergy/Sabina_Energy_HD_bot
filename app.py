import os, re, json, time, requests
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from flask import Flask, request, send_from_directory, jsonify

# ====== Настройки из окружения ======
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
BASE_URL    = os.getenv("BASE_URL", "https://example.onrender.com")
WEBAPP_URL  = os.getenv("WEBAPP_URL", f"{BASE_URL}/hd")
VIDEO_URL   = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
DIRECT_LINK = os.getenv("DIRECT_LINK", "https://human-design.space/")
REDIRECT_BASE_URL = os.getenv("REDIRECT_BASE_URL", "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SabinaSecret")
ADMIN_ID = os.getenv("ADMIN_ID")  # строка; можно не указывать
GS_WEBAPP = os.getenv("GOOGLE_SHEETS_WEBAPP_URL")  # опционально, для лид-магнита

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Хранилище простых состояний (в памяти процесса)
STATE = {}  # user_id -> {"wait_email": bool}
LEADS = []  # сюда складируем полученные email'ы (для отладки)

# ====== Тексты ======
ABOUT_BLOCKS = [
    "✨ *Human Design* — прикладная система самопознания. Она появилась в 1987 году после опыта Ра Уру Ху и объединяет астрологию, И-Цзин, Каббалу, чакровую модель и наблюдения о нейтрино.",
    "🧬 Идея простая: у каждого есть своя механика. Следуя *Стратегии* и *Авторитету*, мы перестаём тратить энергию на сопротивление и начинаем жить в согласии с собой.",
    "🔹 В бодиграфе 9 центров: Корневой, Сакральный, Селезёночный, Солнечное сплетение, Сердечный (Эго), Горловой, Аджна, Теменной и G-центр. Определённые — стабильны, неопределённые — чувствительны к влиянию.",
]

TYPES_SHORT = (
    "В Human Design 5 энергетических типов:\n"
    "• *Манифестор* — инициирует. Стратегия: информировать.\n"
    "• *Генератор* — создаёт через отклик. Стратегия: ждать отклика.\n"
    "• *Манифестирующий Генератор* — быстро+устойчиво. Стратегия: ждать отклика, затем информировать.\n"
    "• *Проектор* — видит других. Стратегия: ждать приглашения.\n"
    "• *Рефлектор* — зеркалит среду. Стратегия: ждать ~28 дней."
)

PROFILES_SHORT = (
    "В Human Design 12 профилей (комбинации линий 1–6), например: 1/3, 2/4, 3/5, 4/6, 5/1, 6/2 и т.д. "
    "Профиль — это «ролевая маска» и стиль обучения/взаимодействия."
)

# Мини-разборы по типам (коротко)
TYPE_BRIEFS = {
    "манифестор": "⚡️ *Манифестор*: вы здесь, чтобы инициировать. Ключ — информировать окружение и беречь энергию на важные импульсы.",
    "генератор": "🔋 *Генератор*: главный двигатель жизни. Идите от отклика тела «да/нет», не тащите то, что не откликается.",
    "манифестирующий генератор": "🚀 *Манифестирующий Генератор*: скорость + устойчивость. Сначала отклик, затем — информировать и действовать итеративно.",
    "проектор": "🎯 *Проектор*: видеть и направлять. Ждите распознавания и приглашений — так ваши таланты раскрываются максимальнее.",
    "рефлектор": "🌙 *Рефлектор*: зеркало среды. Дайте себе цикл Луны для важных решений, берегите пространство и людей вокруг."
}

# Мини-заметки по «эмо/сакр/селез…» и т.п. (если человек пишет «эмоциональный генератор»)
AUTHO_HINTS = {
    "эмоциональный": "💧 *Эмоциональный авторитет*: решения — после волны, не на пике/яме.",
    "сакральный": "🔥 *Сакральный авторитет*: мгновенный отклик тела «угу/неа».",
    "селезёночный": "🫶 *Селезёночный авторитет*: тихая интуиция «здесь и сейчас».",
    "эго": "💪 *Эго-авторитет*: решения из честных желаний/обещаний себе.",
    "ментальный": "🧠 *Ментальный (для проекторов)*: прояснять через обсуждение в правильной среде.",
    "лунный": "🌙 *Лунный (для рефлекторов)*: ориентир — месячный цикл."
}

PROFILE_NAMES = {
    "1/3": "Исследователь / Мученик",
    "1/4": "Исследователь / Оппортунист",
    "2/4": "Отшельник / Оппортунист",
    "2/5": "Отшельник / Еретик",
    "3/5": "Мученик / Еретик",
    "3/6": "Мученик / Ролевая модель",
    "4/6": "Оппортунист / Ролевая модель",
    "4/1": "Оппортунист / Исследователь",
    "5/1": "Еретик / Исследователь",
    "5/2": "Еретик / Отшельник",
    "6/2": "Ролевая модель / Отшельник",
    "6/3": "Ролевая модель / Мученик",
}

# ====== Вспомогательные ======
def tg(method, **params):
    """Вызов Telegram Bot API."""
    try:
        r = requests.post(f"{TG_API}/{method}", json=params, timeout=10)
        return r.json()
    except Exception:
        return {}

def ikb(rows):
    return {"inline_keyboard": rows}

def main_menu():
    return ikb([
        [ {"text":"✨ Что такое Human Design?", "callback_data":"about"} ],
        [ {"text":"📚 Типы и Профили", "callback_data":"types_profiles"} ],
        [ {"text":"✨ Рассчитать бодиграф (бесплатно)", "url": REDIRECT_BASE_URL} ],
        [ {"text":"💎 Платный разбор (отчёт)", "url": DIRECT_LINK} ],
        [ {"text":"🧭 Я знаю свой тип/профиль", "callback_data":"know"} ],
        [ {"text":"💼 Мои услуги", "callback_data":"services"} ],
        [ {"text":"📩 Получить гайд — прислать email", "callback_data":"lead"} ],
    ])

def send_menu(chat_id):
    tg("sendMessage",
       chat_id=chat_id,
       text=("Привет! Это бот Sabina Energy по *Human Design*.\n\n"
             "Здесь можно: почитать основы, сделать расчёт, получить мини-разбор и посмотреть мои услуги."),
       parse_mode="Markdown",
       reply_markup=main_menu())

def build_redirect_url(payload: dict) -> str:
    """
    Собирает ссылку на human-design.space (или другой сайт) + UTM/параметры.
    Сейчас мы без автоподстановки даты/времени (у HDS нет открытого deep-link API).
    """
    parts = urlsplit(REDIRECT_BASE_URL)
    qs = parse_qs(parts.query, keep_blank_values=True)
    # фиксированные utm
    qs.setdefault("utm_source", ["telegram"])
    qs.setdefault("utm_medium", ["bot"])
    qs.setdefault("utm_campaign", ["sabina_hd"])
    # приклеим то, что есть (например, имя/город — просто как метки)
    for k, v in payload.items():
        if v:
            qs[k] = [str(v)]
    new_query = urlencode(qs, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def extract_profile(s: str) -> str | None:
    # ищем 3/5, 3-5, 3.5
    m = re.search(r"\b([1-6])\s*[/\.\-]\s*([1-6])\b", s)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return None

def extract_type_and_autho(s: str):
    # порядок важен — МГ до Генератора
    candidates = [
        "манифестирующий генератор",
        "манифестор",
        "генератор",
        "проектор",
        "рефлектор",
    ]
    t_found = None
    for t in candidates:
        if t in s:
            t_found = t
            break
    # ищем «эмоциональный/сакральный/…»
    a_found = None
    for key in AUTHO_HINTS:
        if key in s:
            a_found = key
            break
    return t_found, a_found

def brief_response(n_type: str|None, profile: str|None, autho: str|None) -> str:
    lines = []
    if n_type:
        lines.append(TYPE_BRIEFS.get(n_type, "").strip())
    if autho:
        lines.append(AUTHO_HINTS.get(autho, "").strip())
    if profile:
        pname = PROFILE_NAMES.get(profile)
        if pname:
            lines.append(f"📖 *Профиль* {profile}: {pname}.")
        else:
            lines.append(f"📖 *Профиль* {profile}.")
    if not lines:
        lines = ["Не смог распознать тип/профиль. Напиши, например: *эмоциональный генератор 3/5*."]
    lines.append("\nЕсли хочешь расширенный разбор — нажми кнопку *«Платный разбор (отчёт)»* ниже.")
    return "\n".join(lines)

# ====== Flask ======
app = Flask(__name__, static_folder="webapp", static_url_path="/hd")

@app.get("/")
def root():
    return "OK"

@app.get("/hd")
def webapp_index():
    # простая статическая страница (если положишь index.html в webapp/)
    try:
        return send_from_directory("webapp", "index.html")
    except Exception:
        return "<h2>SabinaEnergyHD</h2><p>Мини-страница бота.</p>"

@app.get("/hd/<path:fname>")
def webapp_files(fname):
    return send_from_directory("webapp", fname)

@app.get("/webhook-test")
def webhook_test():
    return "Webhook is set", 200

@app.get("/set-webhook")
def set_webhook():
    url = f"{BASE_URL}/tg/webhook"
    r = requests.get(f"{TG_API}/setWebhook",
                     params={"url": url, "secret_token": SECRET_TOKEN},
                     timeout=10)
    return jsonify(r.json())

@app.post("/tg/webhook")
def webhook():
    # проверка секрета
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    if "message" in upd:
        handle_message(upd["message"])
    elif "callback_query" in upd:
        handle_callback(upd["callback_query"])
    return "ok"

# ====== Telegram Handlers ======
def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = normalize_text(msg.get("text", ""))

    # если ждём email
    st = STATE.get(chat_id) or {}
    if st.get("wait_email"):
        email = text
        if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            st["wait_email"] = False
            STATE[chat_id] = st
            # сохраняем локально
            LEADS.append({"chat_id": chat_id, "email": email, "ts": int(time.time())})
            # шлём админу
            if ADMIN_ID:
                tg("sendMessage", chat_id=int(ADMIN_ID),
                   text=f"Новый лид 📩\nchat_id: `{chat_id}`\nemail: `{email}`",
                   parse_mode="Markdown")
            # в Google Sheets (если указан веб-хук Apps Script)
            if GS_WEBAPP:
                try:
                    requests.post(GS_WEBAPP, json={"chat_id": chat_id, "email": email}, timeout=8)
                except Exception:
                    pass
            tg("sendMessage", chat_id=chat_id,
               text="Супер! Гайд отправлю на почту в ближайшее время ✨",
               reply_markup=main_menu())
            return
        else:
            tg("sendMessage", chat_id=chat_id, text="Похоже, это не email. Пришли адрес вида *name@example.com*.", parse_mode="Markdown")
            return

    # команды
    if text.startswith("/start"):
        # привет + «когда рассчитаешь карту — вернись…»
        tg("sendMessage", chat_id=chat_id,
           text=("Когда *рассчитаешь карту* на сайте — вернись сюда и напиши свой *тип* и *профиль*. "
                 "Я пришлю мини-разбор ✨"),
           parse_mode="Markdown")
        send_menu(chat_id)
        return

    if text in ("/menu", "меню"):
        send_menu(chat_id)
        return

    # попытка распознать тип/профиль из свободного текста
    profile = extract_profile(text)
    n_type, autho = extract_type_and_autho(text)
    if profile or n_type:
        tg("sendMessage", chat_id=chat_id,
           text=brief_response(n_type, profile, autho),
           parse_mode="Markdown",
           reply_markup=main_menu())
        return

    # дефолт
    tg("sendMessage", chat_id=chat_id,
       text="Не понял запрос. Нажми кнопку *Меню* и выбери действие, либо напиши, например: «эмоциональный генератор 3/5».",
       parse_mode="Markdown",
       reply_markup=main_menu())

def handle_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data == "about":
        for block in ABOUT_BLOCKS:
            tg("sendMessage", chat_id=chat_id, text=block, parse_mode="Markdown")
        tg("sendMessage", chat_id=chat_id, text=TYPES_SHORT, parse_mode="Markdown")
        tg("sendMessage", chat_id=chat_id, text=PROFILES_SHORT, parse_mode="Markdown",
           reply_markup=main_menu())
        return

    if data == "types_profiles":
        tg("sendMessage", chat_id=chat_id, text=TYPES_SHORT, parse_mode="Markdown")
        tg("sendMessage", chat_id=chat_id, text=PROFILES_SHORT, parse_mode="Markdown",
           reply_markup=ikb([
               [ {"text":"Подробнее о типах", "callback_data":"types_more"} ],
               [ {"text":"Подробнее о профилях", "callback_data":"profiles_more"} ],
               [ {"text":"⬅️ Назад в меню", "callback_data":"back"} ],
           ]))
        return

    if data == "types_more":
        # развернутая выдача по типам
        for key in ["манифестор", "генератор", "манифестирующий генератор", "проектор", "рефлектор"]:
            tg("sendMessage", chat_id=chat_id, text=TYPE_BRIEFS[key], parse_mode="Markdown")
        tg("sendMessage", chat_id=chat_id, text="Готовы сделать расчёт? Нажимай👇",
           reply_markup=ikb([[{"text":"Рассчитать бодиграф", "url": REDIRECT_BASE_URL}],
                             [{"text":"⬅️ Назад в меню", "callback_data":"back"}]]),
           parse_mode="Markdown")
        return

    if data == "profiles_more":
        lines = [f"• *{k}* — {v}" for k, v in PROFILE_NAMES.items()]
        tg("sendMessage", chat_id=chat_id, text="Профили:\n" + "\n".join(lines),
           parse_mode="Markdown",
           reply_markup=ikb([[{"text":"⬅️ Назад в меню", "callback_data":"back"}]]))
        return

    if data == "know":
        tg("sendMessage", chat_id=chat_id,
           text=("Отлично! Пришли сюда свой *тип* + *профиль* — например: "
                 "«эмоциональный генератор 3/5» или «Проектор 4.1»."),
           parse_mode="Markdown")
        return

    if data == "services":
        msg = (
            "💼 *Мои услуги*\n\n"
            "• Разбор с консультацией (90 минут) + отчёт.\n"
            "• Индивидуальные сессии.\n"
            "• Совместимость по Human Design.\n\n"
            "Напиши мне в личку — подберу формат под тебя."
        )
        kb = ikb([
            [ {"text":"Написать в личку", "url":"https://t.me/coachsabina"} ],
            [ {"text":"⬅️ Назад в меню", "callback_data":"back"} ]
        ])
        tg("sendMessage", chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=kb)
        return

    if data == "lead":
        STATE[chat_id] = {"wait_email": True}
        tg("sendMessage", chat_id=chat_id,
           text="Пришли свой email — отправлю гайд 📩\n(введи адрес в ответном сообщении)")
        return

    if data == "back":
        send_menu(chat_id)
        return

# ====== Точка входа для локального запуска ======
if __name__ == "__main__":
    # локально: python app.py
    app.run(host="0.0.0.0", port=8000)
