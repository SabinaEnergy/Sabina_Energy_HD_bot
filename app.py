import os, re, json, requests
from flask import Flask, request, jsonify

# ====== ENV ======
BOT_TOKEN       = os.getenv("BOT_TOKEN", "").strip()    # токен из @BotFather
BASE_URL        = os.getenv("BASE_URL", "https://example.onrender.com").rstrip("/")
SECRET_TOKEN    = os.getenv("SECRET_TOKEN", "SabinaSecret2025")

# Куда вести "бесплатный расчёт" (твоя страница калькулятора на human-design.space с хеш-роутом)
FREE_CALC_URL   = os.getenv(
    "FREE_CALC_URL",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/?rave=7366406054640513"
)

# Куда вести "платный расчёт" (может совпадать; оставила отдельно на случай другой ссылки)
PAID_CALC_URL   = os.getenv(
    "PAID_CALC_URL",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/?rave=7366406054640513"
)

# Видео-инструкция
VIDEO_URL       = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# ====== ТЕЗИСЫ (отредактируй под себя) ======
TYPE_TIPS = {
    "Генератор": (
        "⚡ Генератор: твоя сила — отклик. Слушай «да/нет» тела, а не головы. "
        "Делай то, что зажигает — энергия придёт."
    ),
    "Манифестирующий генератор": (
        "⚡ Манифестирующий Генератор: быстрый старт + мощный отклик. "
        "Можно менять планы по ходу — это нормально."
    ),
    "Манифестор": (
        "⚡ Манифестор: инициируй и информируй. Твоя стратегия — начать и сообщить вовлечённым."
    ),
    "Проектор": (
        "⚡ Проектор: жди признания и приглашения. Фокус на своей экспертизе и правильных людях."
    ),
    "Рефлектор": (
        "⚡ Рефлектор: время — твой друг. Наблюдай циклы, принимай ключевые решения не спеша."
    ),
}

PROFILE_TIPS = {
    "1/3": "🧭 1/3 Исследователь-Экспериментатор: строишь основу и учишься через опыт.",
    "1/4": "🧭 1/4 Исследователь-Оппортунист: фундамент + люди и связи.",
    "2/4": "🧭 2/4 Отшельник-Оппортунист: талантливый интроверт, возможности приходят через людей.",
    "2/5": "🧭 2/5 Отшельник-Еретик: талант + практичность, важно держать границы ожиданий.",
    "3/5": "🧭 3/5 Экспериментатор-Еретик: пробуешь — падаешь — встаёшь и ведёшь других.",
    "3/6": "🧭 3/6 Экспериментатор-Ролевая Модель: три этапа жизни, мудрость через опыт.",
    "4/1": "🧭 4/1 Оппортунист-Исследователь: устойчивость и связи, важен свой фундамент.",
    "4/6": "🧭 4/6 Оппортунист-Ролевая Модель: люди и этапность, к 30+ выходит стабильность.",
    "5/1": "🧭 5/1 Еретик-Исследователь: практичные решения для других, опора на фундамент.",
    "5/2": "🧭 5/2 Еретик-Отшельник: спасатель с талантом, береги энергию и ожидания.",
    "6/2": "🧭 6/2 Ролевая Модель-Отшельник: три этапа жизни, устойчивый пример для других.",
    "6/3": "🧭 6/3 Ролевая Модель-Экспериментатор: мудрость + живой опыт на всех этапах.",
}

# ====== ПАРСЕР ТИПА И ПРОФИЛЯ ======
TYPE_ALIASES = {
    # ключевые слова → нормализованный тип
    r"\bманифестир(ующ|ующий)\s*генератор\b": "Манифестирующий генератор",
    r"\bмг\b": "Манифестирующий генератор",
    r"\bгенератор\b": "Генератор",
    r"\bэмоциональн(ый|ая)\s*генератор\b": "Генератор",  # нормализуем к базовому типу
    r"\bманифестор\b": "Манифестор",
    r"\bпроектор\b": "Проектор",
    r"\bрефлектор\b": "Рефлектор",
}

PROFILE_RE = re.compile(r"(\b[1-6])\s*[/\.]\s*([1-6]\b)")  # 3/5, 3.5, 6 / 2

def extract_type_and_profile(text: str):
    text_lc = text.lower()

    # профиль: ищем первым, он более формален
    prof = None
    m = PROFILE_RE.search(text_lc)
    if m:
        prof = f"{m.group(1)}/{m.group(2)}"

    # тип: пробегаем по алиасам
    t = None
    for pat, norm in TYPE_ALIASES.items():
        if re.search(pat, text_lc):
            t = norm
            break

    return t, prof


# ====== ТЕЛЕГРАМ УТИЛИТЫ ======
def tg_call(method, **params):
    if not BOT_TOKEN:
        return None
    try:
        return requests.post(f"{TG_API}/{method}", json=params, timeout=15)
    except requests.RequestException:
        return None

def main_keyboard():
    return {
        "inline_keyboard": [
            [ {"text": "🧩 Я новичок — расскажи", "callback_data": "novice"} ],
            [ {"text": "🔮 Рассчитать бесплатно", "url": FREE_CALC_URL} ],
            [ {"text": "💎 Платный расчёт", "url": PAID_CALC_URL} ],
            [ {"text": "🎥 Видео / инструкция", "url": VIDEO_URL} ],
            [ {"text": "📝 Я знаю свой тип и профиль", "callback_data": "i_know"} ],
        ]
    }

def novice_flow_messages():
    return [
        "✨ *Что такое Human Design?*\nЭто система самопознания о твоей энергии и способе принимать решения.",
        "🗺 *Бодиграф* — твоя энергетическая карта рождения (центры, каналы, ворота).",
        "🧠 *Тип* подсказывает стратегию взаимодействия с миром. Есть 5 типов.",
        "🧭 *Профиль* — как именно ты пробуешь, учишься, влияешь. Всего 12 комбинаций.",
        "Готова попробовать? Нажми «🔮 Рассчитать бесплатно».",
    ]

# ====== РОУТЫ ======
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
def webhook():
    # защита
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message")
    cq  = upd.get("callback_query")

    # --- нажатия кнопок (callback_data) ---
    if cq:
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data")

        if data == "novice":
            for text in novice_flow_messages():
                tg_call("sendMessage", chat_id=chat_id, text=text, parse_mode="Markdown")
            return "ok"

        if data == "i_know":
            tg_call("sendMessage", chat_id=chat_id,
                    text=("Отправь сюда свой *тип* и *профиль* одним сообщением.\n"
                          "Например: _Эмоциональный генератор 3/5_ или _Проектор 4.1_."),
                    parse_mode="Markdown")
            return "ok"

        # неизвестный колбэк — просто вернём меню
        tg_call("sendMessage", chat_id=chat_id,
                text="Выбери действие ниже 👇",
                reply_markup=main_keyboard())
        return "ok"

    # --- обычные сообщения ---
    if msg:
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        # /start → меню
        if text.startswith("/start"):
            tg_call("sendMessage",
                    chat_id=chat_id,
                    text=("Привет! Это бот Sabina Energy по Human Design.\n\n"
                          "Здесь можно: узнать основы, сделать бесплатный расчёт, "
                          "перейти к полному платному отчёту и посмотреть видео."),
                    reply_markup=main_keyboard())
            return "ok"

        # пробуем разобрать тип и профиль из свободного текста
        t, prof = extract_type_and_profile(text)
        if not t and not prof:
            # не поняли — подскажем формат
            tg_call("sendMessage", chat_id=chat_id,
                    text=("Не поняла 🤔\n"
                          "Отправь свой *тип* и *профиль* одним сообщением.\n"
                          "Примеры: _Манифестирующий генератор 3/5_, _Проектор 4.1_, _Генератор 2/4_."),
                    parse_mode="Markdown",
                    reply_markup=main_keyboard())
            return "ok"

        parts = []
        if t:
            tip = TYPE_TIPS.get(t, "Твой тип — это про стратегию взаимодействия и принятие решений.")
            parts.append(f"Тип: *{t}*\n{tip}")
        if prof:
            tip = PROFILE_TIPS.get(prof, "Твой профиль — ключ к твоим ролям и способу обучения.")
            parts.append(f"Профиль: *{prof}*\n{tip}")

        final = "✅ Вот самое важное по твоей карте:\n\n" + "\n\n".join(parts)
        tg_call("sendMessage", chat_id=chat_id, text=final, parse_mode="Markdown",
                reply_markup={
                    "inline_keyboard":[
                        [ {"text":"🔮 Рассчитать бесплатно", "url": FREE_CALC_URL} ],
                        [ {"text":"💎 Платный расчёт", "url": PAID_CALC_URL} ],
                        [ {"text":"🎥 Видео / инструкция", "url": VIDEO_URL} ],
                    ]
                })
        return "ok"

    return "ok"


if __name__ == "__main__":
    # локальный запуск
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
