# app.py
import os, json, requests
from flask import Flask, render_template, request, jsonify

# ── Настройки Flask: шаблоны в webapp/, статика в webapp/static доступна по /static ──
app = Flask(__name__, template_folder="webapp", static_folder="webapp/static", static_url_path="/static")

# ── ENV (заполни на Render → Settings → Environment) ──
BOT_TOKEN         = os.getenv("BOT_TOKEN", "")  # токен из @BotFather
BASE_URL          = os.getenv("BASE_URL", "https://sabina-energy-hd-bot.onrender.com")
WEBAPP_URL        = os.getenv("WEBAPP_URL", f"{BASE_URL}/hd")  # страница формы
VIDEO_URL         = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
DIRECT_LINK       = os.getenv("DIRECT_LINK", "https://human-design.space?rave=7366406054640513")
SECRET_TOKEN      = os.getenv("SECRET_TOKEN", "SabinaSecret")  # любой твой секрет
TG_API            = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── утилита отправки сообщений в Telegram ──
def tg(method, **params):
    return requests.post(f"{TG_API}/{method}", json=params, timeout=10)

# ── Клавиатура под сообщением ──
def build_keyboard():
    return {
        "inline_keyboard": [
            [ {"text": "Рассчитать бодиграф", "web_app": {"url": WEBAPP_URL}} ],
            [ {"text": "Что с этим делать (видео)", "url": VIDEO_URL} ],
            [ {"text": "Рассчитать на сайте", "url": DIRECT_LINK} ]
        ]
    }

# ── health ──
@app.get("/")
def health():
    return "OK"

# ── твоя страница по /hd ──
@app.get("/hd")
def hd():
    return render_template("index.html")

# ── поставить вебхук для Telegram ──
@app.get("/set-webhook")
def set_webhook():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is empty"})
    url = f"{BASE_URL}/tg/webhook"
    r = requests.get(
        f"{TG_API}/setWebhook",
        params={"url": url, "secret_token": SECRET_TOKEN},
        timeout=10
    )
    try:
        return jsonify(r.json())
    except Exception:
        return r.text, r.status_code

# ── обработчик вебхука ──
@app.post("/tg/webhook")
def webhook():
    # защита: проверяем секрет, который мы задали при setWebhook
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text", "")

    # /start
    if chat_id and text.startswith("/start"):
        tg(
            "sendMessage",
            chat_id=chat_id,
            text=(
                "Привет! Это помощник Sabina Energy по Human Design.\n\n"
                "Нажми «Рассчитать бодиграф», заполни форму и получишь ссылку на расчёт."
            ),
            reply_markup=build_keyboard(),
        )
        return "ok"

    # сюда позже можно добавить разбор web_app_data, когда подключим JS форму
    return "ok"

# ── локальный запуск ──
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
