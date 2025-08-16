import os
import re
import json
import html
import requests
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qs
from flask import Flask, request, send_from_directory, jsonify, abort
from dotenv import load_dotenv

load_dotenv()

# ====== Константы из окружения ======
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
BASE_URL         = os.getenv("BASE_URL", "https://sabina-energy-hd-bot.onrender.com")
WEBAPP_URL       = os.getenv("WEBAPP_URL", f"{BASE_URL}/hd")
VIDEO_URL        = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
DIRECT_LINK      = os.getenv("DIRECT_LINK", "https://human-design.space/?rave=")
REDIRECT_BASE_URL = os.getenv("REDIRECT_BASE_URL", "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")
SERVICES_URL     = os.getenv("SERVICES_URL", "")
SECRET_TOKEN     = os.getenv("SECRET_TOKEN", "SabinaSecret")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ====== Flask ======
app = Flask(__name__, static_folder="webapp", static_url_path="/hd")

# ====== Вспомогалки Telegram ======
def tg(method, **params):
    """Вызов Telegram Bot API (json)."""
    try:
        r = requests.post(f"{TG_API}/{method}", json=params, timeout=10)
        return r.json()
    except Exception as e:
        print("TG error:", e)
        return {"ok": False, "error": str(e)}

def send_msg(chat_id, text, **kw):
    return tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", **kw)

def send_menu(chat_id):
    kb = {
        "inline_keyboard": [
            [ {"text": "✨ Рассчитать бодиграф (анкета)", "callback_data": "flow_calc"} ],
            [ {"text": "💎 Платный расчёт", "url": DIRECT_LINK or "https://human-design.space/"} ],
            [ {"text": "🎥 Видео / инструкция", "url": VIDEO_URL} ],
            [ {"text": "ℹ️ Что такое Human Design?", "callback_data": "about_hd"} ],
            [
                {"text": "📚 О типах", "callback_data": "about_types"},
                {"text": "📖 О профилях", "callback_data": "about_profiles"},
            ],
            [ {"text": "📝 Я знаю свой тип/профиль", "callback_data": "i_know"} ],
        ]
    }
    if SERVICES_URL:
        kb["inline_keyboard"].append([{"text": "🛠 Мои услуги", "url": SERVICES_URL}])
    send_msg(chat_id, START_TEXT, reply_markup=kb)

# ====== Тексты ======
START_TEXT = (
    "Привет! Это бот <b>Sabina Energy</b> по Human Design.\n\n"
    "Здесь можно: сделать бесплатный расчёт (анкета), узнать основы, перейти к платному отчёту и посмотреть видео."
)

ABOUT_HD = (
    "<b>Что такое Human Design</b>\n\n"
    "• Система появилась в 1987 году (Ра Уру Ху). Синтез астрологии, И-Цзин, Каббалы, чакровой модели и идей физики.\n"
    "• Цель — жить в согласии со своей природой, следуя стратегии и авторитету.\n"
    "• В основе — идея “информации нейтрино”, отпечаток которой фиксируется в бодиграфе.\n"
    "• 9 центров: Корневой, Сакральный, Селезёночный, Солн. сплетение, Сердечный (Эго), Горловой, Аджна, Теменной, G-центр.\n"
    "Определённые центры — стабильная энергия; неопределённые — чувствительность к внешнему влиянию."
)

ABOUT_TYPES = (
    "<b>Типы и стратегии</b>\n"
    "• <b>Манифестор</b> — инициирует. Стратегия: информировать перед действиями.\n"
    "• <b>Генератор</b> — создаёт, действует стабильно. Стратегия: ждать отклика.\n"
    "• <b>Манифестирующий генератор</b> — быстрое действие + устойчивость. Стратегия: ждать отклика, затем информировать.\n"
    "• <b>Проектор</b> — видит и направляет. Стратегия: ждать приглашения.\n"
    "• <b>Рефлектор</b> — зеркалит среду. Стратегия: ждать ~28 дней (цикл Луны) для важных решений."
)

ABOUT_PROFILES = (
    "<b>Профили</b> — комбинации двух линий (1–6). Всего 12 вариантов:\n"
    "1/3, 1/4, 2/4, 2/5, 3/5, 3/6, 4/6, 4/1, 5/1, 5/2, 6/2, 6/3.\n"
    "Каждый профиль — особая роль/поведение: исследование, взаимодействие, проб и ошибок, ереси и т.п."
)

TYPE_SNIPPETS = {
    "манифестор": "Манифестор — инициатор. Важна независимость и информирование окружающих перед шагами.",
    "генератор": "Генератор — устойчивая жизненная энергия. Главный инструмент — сакральный отклик.",
    "манифестирующий генератор": "Манифестирующий генератор — быстро и мощно. Сначала отклик, затем информирование.",
    "проектор": "Проектор — направляет других. Важны признание и приглашение.",
    "рефлектор": "Рефлектор — зеркалит среду, меняется с лунным циклом. Решения после полного лунного цикла.",
}

PROFILE_SNIPPETS = {
    "1/3": "1/3 — Исследователь / Мученик: сначала разобраться, затем опыт через пробу и ошибку.",
    "1/4": "1/4 — Исследователь / Оппортунист: фундамент + влияние через близкие связи.",
    "2/4": "2/4 — Отшельник / Оппортунист: талант в тишине, проявление через окружение.",
    "2/5": "2/5 — Отшельник / Еретик: практичные решения, к вам проецируют ожидания.",
    "3/5": "3/5 — Мученик / Еретик: обучение через опыт, вы умеете чинить сломанное.",
    "3/6": "3/6 — Мученик / Ролевая модель: этапы — опыт, обзор, пример для других.",
    "4/6": "4/6 — Оппортунист / Ролевая модель: сила в отношениях и примером.",
    "4/1": "4/1 — Оппортунист / Исследователь: стабильная основа + влияние через связи.",
    "5/1": "5/1 — Еретик / Исследователь: проекции пользы, нужен прочный фундамент.",
    "5/2": "5/2 — Еретик / Отшельник: практичные решения + природные дары в уединении.",
    "6/2": "6/2 — Ролевая модель / Отшельник: цикл 3х фаз, затем пример другим.",
    "6/3": "6/3 — Ролевая модель / Мученик: долгий путь опытов к зрелой модели.",
}

# ====== Простая память состояний (в RAM) ======
STATE = {}  # chat_id -> {"step": "...", "data": {...}}

def start_flow(chat_id):
    STATE[chat_id] = {"step": "ask_date", "data": {}}
    send_msg(chat_id, "Укажи дату рождения (формат: <b>22.10.1985</b>).")

def handle_flow(chat_id, text):
    st = STATE.get(chat_id, {"step": None, "data": {}})
    step = st.get("step")

    if step == "ask_date":
        if not re.match(r"^\d{1,2}\.\d{1,2}\.\d{4}$", text.strip()):
            return send_msg(chat_id, "Пожалуйста, дата в формате <b>дд.мм.гггг</b> 🙏")
        st["data"]["date"] = text.strip()
        st["step"] = "ask_time"
        send_msg(chat_id, "Время рождения ⏰ (например: <b>15:03</b>). Если не знаешь — напиши «утро», «день» или «вечер».")
        return

    if step == "ask_time":
        st["data"]["time"] = text.strip()
        st["step"] = "ask_city"
        send_msg(chat_id, "Город/место рождения 🌍 (например: <b>Москва</b>).")
        return

    if step == "ask_city":
        st["data"]["city"] = text.strip()
        data = st["data"]
        STATE.pop(chat_id, None)

        # Ссылка на расчёт — ведём на страницу создания карты,
        # где пользователь уже нажмёт «Построить карту».
        calc_url = REDIRECT_BASE_URL

        msg = (
            "Отлично, данные получили ✅\n\n"
            "🔮 Перейди по ссылке и посмотри свой бодиграф:\n"
            f"{calc_url}\n\n"
            "Когда увидишь <b>тип</b> и <b>профиль</b> — просто напиши их сюда, например:\n"
            "«эмоциональный генератор 3/5» или «Проектор 4.1».\n\n"
            "А пока — можно сохранить ссылку на продвинутый расчёт:\n"
        )
        kb = {
            "inline_keyboard": [
                [ {"text": "Перейти к расчёту", "url": calc_url} ],
                [ {"text": "💎 Платный расчёт", "url": DIRECT_LINK or "https://human-design.space/"} ],
            ]
        }
        send_msg(chat_id, msg, reply_markup=kb)
        return

    # Если шаг потерян — перезапускаем
    send_msg(chat_id, "Давай начнём заново 😊")
    start_flow(chat_id)

# ====== Парсинг типа/профиля из текста ======
TYPE_KEYS = [
    ("манифестирующий генератор", "манифестирующий генератор"),
    ("генератор", "генератор"),
    ("манифестор", "манифестор"),
    ("проектор", "проектор"),
    ("рефлектор", "рефлектор"),
]

PROFILE_RE = re.compile(r"(\d)\s*[./]\s*(\d)")

def mini_reading_from_text(text):
    low = text.lower()
    found_type = None
    for key, norm in TYPE_KEYS:
        if key in low:
            found_type = norm
            break
    m = PROFILE_RE.search(low)
    prof = None
    if m:
        prof = f"{m.group(1)}/{m.group(2)}"

    parts = []
    if found_type:
        parts.append(f"<b>Тип:</b> {found_type.capitalize()}\n{TYPE_SNIPPETS.get(found_type,'')}")
    if prof and prof in PROFILE_SNIPPETS:
        parts.append(f"\n<b>Профиль:</b> {prof}\n{PROFILE_SNIPPETS[prof]}")
    if not parts:
        return None
    return "\n".join(parts)

# ====== Построение ссылок (если решишь добавлять UTM или реферал) ======
FIXED_UTM = {"utm_source":"telegram","utm_medium":"bot","utm_campaign":"sabina_hd_bot"}
def add_utm(url, extra=None):
    extra = extra or {}
    p = urlsplit(url)
    qs = parse_qs(p.query, keep_blank_values=True)
    for k,v in FIXED_UTM.items():
        qs.setdefault(k, [v])
    for k,v in extra.items():
        if v is None: 
            continue
        qs[k] = [str(v)]
    new_q = urlencode(qs, doseq=True)
    return urlunsplit((p.scheme, p.netloc, p.path, new_q, p.fragment))

# ====== Роуты сервера ======
@app.get("/")
def health():
    return "OK"

@app.get("/hd")
def hd_index():
    # отдаём index.html из папки webapp
    return send_from_directory("webapp", "index.html")

@app.get("/hd/<path:fname>")
def hd_static(fname):
    return send_from_directory("webapp", fname)

@app.get("/privacy")
def privacy():
    return send_from_directory("static", "privacy.html")

@app.get("/set-webhook")
def set_webhook():
    url = f"{BASE_URL}/tg/webhook"
    r = requests.get(
        f"{TG_API}/setWebhook",
        params={"url": url, "secret_token": SECRET_TOKEN},
        timeout=10
    )
    return jsonify(r.json())

@app.get("/check-webhook")
def check_webhook():
    r = requests.get(f"{TG_API}/getWebhookInfo", timeout=10)
    return jsonify(r.json())

@app.post("/tg/webhook")
def webhook():
    # защита секретом
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        abort(403)

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message")
    cb  = upd.get("callback_query")

    # Callback-кнопки
    if cb:
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data") or ""
        # Закроем "часики"
        tg("answerCallbackQuery", callback_query_id=cb["id"])
        if data == "flow_calc":
            start_flow(chat_id)
        elif data == "about_hd":
            send_msg(chat_id, ABOUT_HD)
        elif data == "about_types":
            send_msg(chat_id, ABOUT_TYPES)
        elif data == "about_profiles":
            send_msg(chat_id, ABOUT_PROFILES)
        elif data == "i_know":
            send_msg(chat_id, "Напиши сюда свой <b>тип</b> и <b>профиль</b>, например: «эмоциональный генератор 3/5» или «Проектор 4.1».")
        else:
            send_menu(chat_id)
        return "ok"

    # Обычные сообщения
    if msg:
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        if text.startswith("/start"):
            send_menu(chat_id)
            return "ok"

        # Если пользователь в анкете — ведём по шагам
        if chat_id in STATE and STATE[chat_id].get("step"):
            handle_flow(chat_id, text)
            return "ok"

        # Пытаемся распознать тип/профиль и дать мини-разбор
        reading = mini_reading_from_text(text)
        if reading:
            send_msg(chat_id, reading)
            kb = {
                "inline_keyboard":[
                    [ {"text":"🎓 Больше об основах", "callback_data":"about_hd"} ],
                    [ {"text":"💎 Платный расчёт", "url": DIRECT_LINK or "https://human-design.space/"} ],
                ]
            }
            send_msg(chat_id, "Хочешь продолжить? Выбери, что дальше:", reply_markup=kb)
            return "ok"

        # Любой другой текст — покажем меню
        send_msg(chat_id, "Выбери действие 👇")
        send_menu(chat_id)
        return "ok"

    return "ok"

# ====== Локальный запуск (на Render не используется) ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
