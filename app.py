import os, re, json, requests
from urllib.parse import urlencode
from flask import Flask, request, jsonify

# ── ENV ──────────────────────────────────────────────────────────────────────
BOT_TOKEN         = os.getenv("BOT_TOKEN")                          # токен бота
BASE_URL          = os.getenv("BASE_URL", "https://example.onrender.com")  # твой Render url
FREE_CALC_URL     = os.getenv("FREE_CALC_URL",  # калькулятор HDS (бесплатный)
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")
PAID_URL          = os.getenv("PAID_URL", "https://human-design.space/?rave=YOUR_REF")
VIDEO_URL         = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
LEAD_FORM_URL     = os.getenv("LEAD_FORM_URL", "https://forms.gle/your_google_form")
SECRET_TOKEN      = os.getenv("SECRET_TOKEN", "SabinaSecret")       # для вебхука

TG = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Flask ────────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ── Короткие тексты (ликбез) ────────────────────────────────────────────────
INFO_BLOCKS = [
    "🌟 *Human Design* — современная система самопознания.\nОна соединяет астрологию, И-Цзин, Каббалу, чакровую модель и наблюдения за нейтрино.",
    "🧠 *Идея простая:* не менять себя, а жить в согласии со своей природой. Ключ — следовать *Стратегии* и *Авторитету*.",
    "🔹 *Типы:* Манифестор, Генератор, Манифестирующий Генератор, Проектор, Рефлектор.",
    "📚 *Профили:* всего 12 комбинаций (1/3, 1/4, 2/4, 2/5, 3/5, 3/6, 4/6, 4/1, 5/1, 5/2, 6/2, 6/3).",
]

TYPE_TIPS = {
    "манифестор":
        "⚡️ *Манифестор* — инициирует и прокладывает путь. Стратегия: _информировать перед действием_.",
    "генератор":
        "🔋 *Генератор* — стабильная энергия и реализация через отклик. Стратегия: _ждать отклика_.",
    "манифестирующий генератор":
        "🚀 *Манифестирующий генератор* — скорость + устойчивость. Стратегия: _ждать отклика_, затем _информировать_.",
    "проектор":
        "🎯 *Проектор* — видит других и направляет. Стратегия: _ждать приглашения_.",
    "рефлектор":
        "🌙 *Рефлектор* — усиленно чувствует среду. Стратегия: _ждать лунный цикл (≈28 дней)_.",
}

# Короткие подсказки по авторитетам (подмешаем, если встречается в тексте)
AUTH_TIPS = {
    "эмоцион": "🌊 *Эмоциональный авторитет:* решения — только _после волны_, не на пике эмоций.",
    "сакрал":  "🔥 *Сакральный авторитет:* доверяй мгновенному телесному отклику «угу/не-угу».",
    "селез":  "🫶 *Селезёночный авторитет:* тихая интуиция «здесь и сейчас».",
    "эго":     "💪 *Эго-авторитет:* «хочу/могу, мне это правда нужно?» — честность с собой.",
    "g-":      "💖 *G-авторитет:* ориентир — чувство правильного направления/идентичности.",
    "ментал":  "🧩 *Ментальный (у проекторов):* обсуждай вслух с безопасными людьми.",
    "лун":     "🌙 *Лунный (у рефлекторов):* прожди ~28 дней и наблюдай.",
}

PROFILE_TITLES = {
    "1/3":"1/3 — Исследователь/Мученик", "1/4":"1/4 — Исследователь/Оппортунист",
    "2/4":"2/4 — Отшельник/Оппортунист", "2/5":"2/5 — Отшельник/Еретик",
    "3/5":"3/5 — Мученик/Еретик",        "3/6":"3/6 — Мученик/Ролевая модель",
    "4/6":"4/6 — Оппортунист/Ролевая модель","4/1":"4/1 — Оппортунист/Исследователь",
    "5/1":"5/1 — Еретик/Исследователь",  "5/2":"5/2 — Еретик/Отшельник",
    "6/2":"6/2 — Ролевая модель/Отшельник","6/3":"6/3 — Ролевая модель/Мученик",
}
PROFILE_TIPS = {
    "1/3":"🔎 Основа — исследование и личный опыт/ошибки → устойчивость.",
    "1/4":"🤝 Глубина + сила окружения/связей. Знание приносит возможности.",
    "2/4":"🏡 Нужны время на «дом/тишину» и правильные люди/приглашения.",
    "2/5":"🧭 Природный талант + практичные решения для других. Береги границы.",
    "3/5":"🧪 Обучение через опыт + умение чинить и упрощать для других.",
    "3/6":"🧗 Этапность пути: опыт → наблюдение → роль модели.",
    "4/6":"👥 Стабильность через связи, позже — мудрость и пример.",
    "4/1":"🧱 Непоколебимая основа + сила контактов. Важно стоять на своём.",
    "5/1":"🦸‍♀️ Проекционный образ «спасателя» + надёжная база знаний.",
    "5/2":"🦉 Скромный талант, который видят другие. Береги энергию.",
    "6/2":"🌿 Естественность + путь к роли модели к 3му циклу жизни.",
    "6/3":"🌀 Много опыта/перепроб, затем — взросление до мудрой роли.",
}

# ── Состояния (простая память в RAM) ────────────────────────────────────────
waiting_type_profile = set()  # chat_id тех, кто нажал «Я знаю свой тип/профиль»

# ── Вспомогалки ─────────────────────────────────────────────────────────────
def tg(method, **params):
    return requests.post(f"{TG}/{method}", json=params, timeout=10)

def main_menu():
    return {
        "inline_keyboard":[
            [{"text":"✨ Рассчитать бодиграф (анкета)", "url": FREE_CALC_URL}],
            [{"text":"💎 Платный отчёт", "url": PAID_URL}],
            [{"text":"🎥 Видео / инструкция", "url": VIDEO_URL}],
            [{"text":"ℹ️ Что такое Human Design?", "callback_data":"info_hd"}],
            [
                {"text":"📚 О типах", "callback_data":"info_types"},
                {"text":"📖 О профилях", "callback_data":"info_profiles"}
            ],
            [{"text":"📝 Я знаю свой тип/профиль", "callback_data":"i_know"}],
            [{"text":"🎁 Получить PDF-гайд", "url": LEAD_FORM_URL}],
            [{"text":"💼 Мои услуги", "callback_data":"services"}],
        ]
    }

def send_blocks(chat_id, blocks):
    # отправляем несколько сообщений подряд
    for b in blocks:
        tg("sendMessage", chat_id=chat_id, text=b, parse_mode="Markdown")

def parse_type(text):
    t = text.lower()
    if "манифестир" in t and "генератор" in t: return "манифестирующий генератор"
    for key in ["манифестор", "генератор", "проектор", "рефлектор"]:
        if key in t: return key
    return None

def parse_authority(text):
    t = text.lower()
    for key, tip in AUTH_TIPS.items():
        if key in t:  # ищем кусочек слова: эмоц, сакрал, селез, лун…
            return tip
    return None

def parse_profile(text):
    m = re.search(r'([1-6])\s*[./]\s*([1-6])', text)
    if not m: return None
    return f"{m.group(1)}/{m.group(2)}"

# ── Роуты ───────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return "OK"

@app.get("/set-webhook")
def set_webhook():
    url = f"{BASE_URL}/tg/webhook"
    r = requests.get(f"{TG}/setWebhook",
                     params={"url": url, "secret_token": SECRET_TOKEN}, timeout=10)
    return jsonify(r.json())

@app.post("/tg/webhook")
def webhook():
    # безопасность вебхука
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    # обработка callback
    if "callback_query" in upd:
        cq = upd["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data","")

        if data == "info_hd":
            send_blocks(chat_id, INFO_BLOCKS)
            tg("sendMessage", chat_id=chat_id,
               text="Хочешь попробовать расчёт? Жми кнопку ниже 👇",
               reply_markup=main_menu())
        elif data == "info_types":
            tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
               text=("*Типы:* Манифестор, Генератор, Манифестирующий "
                     "Генератор, Проектор, Рефлектор.\n\n"
                     "Следуй Стратегии и Авторитету — это ключ! 🔑"))
        elif data == "info_profiles":
            tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
               text=("Всего *12 профилей*: 1/3, 1/4, 2/4, 2/5, 3/5, 3/6, "
                     "4/6, 4/1, 5/1, 5/2, 6/2, 6/3.\n"
                     "Профиль — это твой стиль взаимодействия с миром."))
        elif data == "i_know":
            waiting_type_profile.add(chat_id)
            tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
               text=("Отлично! Напиши сюда одним сообщением *тип* и *профиль*.\n"
                     "Например: `эмоциональный генератор 3/5` или `Проектор 4.1`"))
        elif data == "services":
            tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
               text=("💼 *Мои услуги*\n"
                     "• Индивидуальный разбор (90 минут) + письменный отчёт.\n"
                     "• Разбор типа/профиля, стратегии/авторитета.\n\n"
                     "Напиши мне в личные сообщения: @coachsabina"))
        return "ok"

    # обычные сообщения
    msg = upd.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()

    if not text:
        return "ok"

    if text.lower().startswith("/start"):
        tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
           text=("Привет! Это бот *Sabina Energy* по Human Design.\n\n"
                 "Здесь можно: сделать бесплатный расчёт (анкета), "
                 "узнать основы, перейти к платному отчёту и посмотреть видео."),
           reply_markup=main_menu())
        # подсказка к бесплатному расчёту
        tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
           text=("Когда *рассчитаешь карту* на сайте — вернись сюда и "
                 "напиши свой *тип* и *профиль*. Я пришлю мини-разбор ✨"))
        return "ok"

    # Если ждём от пользователя тип/профиль
    if chat_id in waiting_type_profile:
        waiting_type_profile.discard(chat_id)

        user_type = parse_type(text)            # «генератор», «проектор»…
        profile   = parse_profile(text)         # «3/5» и т.п.
        authority_tip = parse_authority(text)   # если попадётся «эмоцион…», «сакрал…»

        parts = []
        if user_type:
            parts.append(TYPE_TIPS.get(user_type, f"Тип: *{user_type}*"))
        if authority_tip:
            parts.append(authority_tip)
        if profile:
            title = PROFILE_TITLES.get(profile, f"Профиль {profile}")
            parts.append(f"**{title}**\n{PROFILE_TIPS.get(profile,'')}".replace("**","*"))
        if not parts:
            parts = ["Не смог распознать тип/профиль 🤔 Напиши, пожалуйста, в формате: "
                     "`эмоциональный генератор 3/5` или `Проектор 4.1`."]

        # ответ + CTA
        parts.append(f"\nХочешь глубже? 💎 Подробный отчёт здесь: {PAID_URL}")
        tg("sendMessage", chat_id=chat_id, parse_mode="Markdown",
           text="\n\n".join(parts), reply_markup=main_menu())
        return "ok"

    # Фолбэк: показываем меню
    tg("sendMessage", chat_id=chat_id, text="Выбери действие из меню 👇",
       reply_markup=main_menu())
    return "ok"

# ── Local run ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
