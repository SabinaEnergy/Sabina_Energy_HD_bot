import os, re, json, time, requests
from flask import Flask, request, jsonify

# ========== ENV ==========
BOT_TOKEN    = os.getenv("BOT_TOKEN", "").strip()          # токен из @BotFather
BASE_URL     = os.getenv("BASE_URL", "https://example.com").rstrip("/")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SabinaSecret2025")

# куда вести на бесплатный/платный расчёт (твоя рефералка и/или калькулятор)
FREE_CALC_URL = os.getenv(
    "FREE_CALC_URL",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/?rave=7366406054640513"
)
PAID_CALC_URL = os.getenv(
    "PAID_CALC_URL",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/?rave=7366406054640513"
)
VIDEO_URL    = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# ========== ХРАНИЛИЩЕ СОСТОЯНИЙ (in-memory) ==========
# sessions[user_id] = {"step": "...", "data": {...}, "ts": unix}
sessions = {}

# ========== ТЕЗИСЫ (заглушки — потом подставишь свои тексты) ==========
TYPE_TIPS = {
    "Генератор": "⚡ Генератор: жди отклика тела. Делай то, что зажигает — энергия придёт.",
    "Манифестирующий генератор": "⚡ МГ: быстрый старт + отклик. Менять курс по ходу — ок.",
    "Манифестор": "⚡ Манифестор: инициируй и информируй вовлечённых.",
    "Проектор": "⚡ Проектор: жди признания/приглашения. Фокус на своей экспертизе.",
    "Рефлектор": "⚡ Рефлектор: решения не спеши — наблюдай циклы (до лунного).",
}

PROFILE_TIPS = {
    "1/3": "🧭 1/3 Исследователь-Экспериментатор: фундамент + обучение на опыте.",
    "1/4": "🧭 1/4 Исследователь-Оппортунист: опора + связи/люди.",
    "2/4": "🧭 2/4 Отшельник-Оппортунист: талант + возможности через людей.",
    "2/5": "🧭 2/5 Отшельник-Еретик: талантлив и практичен, береги границы ожиданий.",
    "3/5": "🧭 3/5 Экспериментатор-Еретик: пробуй — делай выводы — веди.",
    "3/6": "🧭 3/6 Экспериментатор-Ролевая модель: три этапа жизни → мудрость.",
    "4/1": "🧭 4/1 Оппортунист-Исследователь: устойчивость + важны контакты.",
    "4/6": "🧭 4/6 Оппортунист-Ролевая модель: люди + этапность пути.",
    "5/1": "🧭 5/1 Еретик-Исследователь: практичные решения + опора на фундамент.",
    "5/2": "🧭 5/2 Еретик-Отшельник: спасатель с талантом, береги энергию.",
    "6/2": "🧭 6/2 Ролевая модель-Отшельник: стабильный пример с возрастом.",
    "6/3": "🧭 6/3 Ролевая модель-Экспериментатор: мудрость + живой опыт.",
}

# ========== ПАРСИНГ ТИПА/ПРОФИЛЯ из текста ==========
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

# ========== TELEGRAM HELPERS ==========
def tg(method, **params):
    if not BOT_TOKEN: return None
    try:
        return requests.post(f"{TG_API}/{method}", json=params, timeout=15)
    except requests.RequestException:
        return None

def main_menu():
    return {
        "inline_keyboard":[
            [ {"text":"✨ Рассчитать бодиграф (анкета)","callback_data":"calc_start"} ],
            [ {"text":"💎 Платный расчёт","url": PAID_CALC_URL} ],
            [ {"text":"🎥 Видео / инструкция","url": VIDEO_URL} ],
            [ {"text":"ℹ️ Что такое Human Design?","callback_data":"about_hd"} ],
            [ {"text":"📚 О типах","callback_data":"about_types"},
              {"text":"📖 О профилях","callback_data":"about_profiles"} ],
            [ {"text":"📝 Я знаю свой тип/профиль","callback_data":"i_know"} ],
        ]
    }

def about_hd_messages():
    return [
        "✨ *Human Design* — система о твоей энергии и принятии решений.",
        "🗺 *Бодиграф* — карта центров/каналов/ворот, формируется по дате/времени/месту.",
        "🧠 *Тип* — стратегия взаимодействия с миром. Всего 5 типов.",
        "🧭 *Профиль* — как ты учишься и влияешь. 12 сочетаний.",
        "Готова попробовать? Жми «✨ Рассчитать бодиграф (анкета)».",
    ]

# ========== АНКЕТА (простая FSM) ==========
def start_session(uid):
    sessions[uid] = {"step": "ask_date", "data": {}, "ts": time.time()}

def cleanup_sessions(max_age_sec=3600):
    now = time.time()
    for uid in list(sessions.keys()):
        if now - sessions[uid].get("ts", now) > max_age_sec:
            sessions.pop(uid, None)

def fsm_handle(uid, text):
    s = sessions.get(uid) or {}
    step = s.get("step")
    data = s.get("data", {})
    s["ts"] = time.time()

    if step == "ask_date":
        data["birth_date"] = text.strip()
        s["step"] = "ask_time"
        s["data"] = data
        sessions[uid] = s
        return "Время рождения ⏰ (например: 15:03). Если не знаешь — напиши «утро», «день» или «вечер»."

    if step == "ask_time":
        data["birth_time"] = text.strip()
        s["step"] = "ask_place"
        s["data"] = data
        sessions[uid] = s
        return "Город/место рождения 🌍 (например: Москва, Россия)."

    if step == "ask_place":
        data["birth_place"] = text.strip()
        s["step"] = "done"
        sessions[uid] = s

        # собираем ссылку (передаём параметры для аналитики, сайт сам не автозаполнит)
        params = {
            "date": data.get("birth_date",""),
            "time": data.get("birth_time",""),
            "place": data.get("birth_place",""),
            "utm_source": "telegram-bot",
            "utm_medium": "funnel",
        }
        # добавим в HASH-часть только rave (основной трекинг)
        link = FREE_CALC_URL

        msg = (
            "Отлично, данные получили ✅\n\n"
            "🔮 Перейди по ссылке и посмотри свой бодиграф:\n"
            f"{link}\n\n"
            "Когда увидишь *тип* и *профиль* — просто напиши их сюда, например:\n"
            "«эмоциональный генератор 3/5» или «Проектор 4.1»."
        )
        return msg

    # если что-то пошло не так — сброс
    start_session(uid)
    return "Давай начнём сначала. Укажи дату рождения (формат: 22.10.1985)."

# ========== FLASK ROUTES ==========
@app.get("/")
def health():
    return "OK"

@app.get("/set-webhook")
def set_webhook():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is empty"})
    url = f"{BASE_URL}/tg/webhook"
    r = requests.get(f"{TG_API}/setWebhook",
                     params={"url": url, "secret_token": SECRET_TOKEN},
                     timeout=15)
    try: return jsonify(r.json())
    except Exception: return r.text, r.status_code

@app.get("/get-webhook-info")
def get_wh_info():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is empty"})
    r = requests.get(f"{TG_API}/getWebhookInfo", timeout=15)
    try: return jsonify(r.json())
    except Exception: return r.text, r.status_code

@app.post("/tg/webhook")
def tg_webhook():
    # защита вебхука
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message")
    cb  = upd.get("callback_query")

    # ---- callback-кнопки ----
    if cb:
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data","")

        if data == "calc_start":
            start_session(chat_id)
            tg("sendMessage", chat_id=chat_id,
               text="Анкета ✍️\nУкажи дату рождения (формат: 22.10.1985).")
            return "ok"

        if data == "about_hd":
            for t in about_hd_messages():
                tg("sendMessage", chat_id=chat_id, text=t, parse_mode="Markdown")
            return "ok"

        if data == "about_types":
            tg("sendMessage", chat_id=chat_id,
               text=("5 типов: Генератор, Манифестирующий Генератор, Проектор, "
                     "Манифестор, Рефлектор.\n"
                     "Узнай свой тип через «✨ Рассчитать бодиграф (анкета)»."))
            return "ok"

        if data == "about_profiles":
            tg("sendMessage", chat_id=chat_id,
               text=("Профиль — это 2 цифры (например, 3/5, 2/4, 6/2). "
                     "Они показывают стиль обучения и влияния.\n"
                     "Узнай свой профиль через «✨ Рассчитать бодиграф (анкета)»."))
            return "ok"

        if data == "i_know":
            tg("sendMessage", chat_id=chat_id,
               text=("Отправь свой *тип* и *профиль* одним сообщением.\n"
                     "Примеры: _Манифестирующий генератор 3/5_, _Проектор 4.1_, _Генератор 2/4_."),
               parse_mode="Markdown")
            return "ok"

        # по умолчанию — показать меню
        tg("sendMessage", chat_id=chat_id,
           text="Выбери действие 👇", reply_markup=main_menu())
        return "ok"

    # ---- обычные сообщения ----
    if msg:
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        # /start → меню
        if text.startswith("/start"):
            cleanup_sessions()
            tg("sendMessage", chat_id=chat_id,
               text=("Привет! Это бот Sabina Energy по Human Design.\n\n"
                     "Здесь можно: сделать бесплатный расчёт (анкета), узнать основы, "
                     "перейти к платному отчёту и посмотреть видео."),
               reply_markup=main_menu())
            return "ok"

        # если пользователь в анкете — ведём по шагам
        if chat_id in sessions and sessions[chat_id].get("step") in {"ask_date","ask_time","ask_place"}:
            reply = fsm_handle(chat_id, text)
            tg("sendMessage", chat_id=chat_id, text=reply, parse_mode="Markdown")
            return "ok"

        # иначе пытаемся распознать тип/профиль из текста
        t, prof = extract_type_and_profile(text)
        if not t and not prof:
            tg("sendMessage", chat_id=chat_id,
               text=("Не поняла 🤔\n"
                     "Отправь свой *тип* и *профиль* одним сообщением.\n"
                     "Примеры: _Манифестирующий генератор 3/5_, _Проектор 4.1_, _Генератор 2/4_."),
               parse_mode="Markdown",
               reply_markup=main_menu())
            return "ok"

        parts = []
        if t:
            parts.append(f"Тип: *{t}*\n{TYPE_TIPS.get(t,'Твой тип — твоя стратегия взаимодействия.')}")
        if prof:
            parts.append(f"Профиль: *{prof}*\n{PROFILE_TIPS.get(prof,'Профиль — про роли и способ обучения.')}")

        final = "✅ Твоё краткое резюме:\n\n" + "\n\n".join(parts)
        tg("sendMessage", chat_id=chat_id, text=final, parse_mode="Markdown",
           reply_markup={
               "inline_keyboard":[
                   [ {"text":"🔮 Перейти к расчёту","url": FREE_CALC_URL} ],
                   [ {"text":"💎 Платный расчёт","url": PAID_CALC_URL} ],
                   [ {"text":"🎥 Видео / инструкция","url": VIDEO_URL} ],
               ]
           })
        return "ok"

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
