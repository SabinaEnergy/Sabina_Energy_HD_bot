# app.py — работает и в Telegram, и в браузере: редирект + сообщение в чат
import os, json, requests
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from flask import Flask, render_template, request, jsonify, redirect

app = Flask(
    __name__,
    template_folder="webapp",          # HTML-шаблоны лежат в webapp/
    static_folder="webapp/static",     # статика (CSS/JS) лежит в webapp/static
    static_url_path="/static",
)

# ===== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (Render → Settings → Environment) =====
BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
BASE_URL     = os.getenv("BASE_URL", "https://sabina-energy-hd-bot.onrender.com")
WEBAPP_URL   = os.getenv("WEBAPP_URL", f"{BASE_URL}/hd")
VIDEO_URL    = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
DIRECT_LINK  = os.getenv("DIRECT_LINK", "https://human-design.space?rave=7366406054640513")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SabinaSecret")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# UTM-метки по умолчанию (добавляем, если их нет в ссылке)
FIXED_UTM = {
    "utm_source": "telegram",
    "utm_medium": "bot",
    "utm_campaign": "sabina_hd_bot",
}

def tg(method, **params):
    """Вызов Telegram Bot API."""
    return requests.post(f"{TG_API}/{method}", json=params, timeout=10)

def build_keyboard():
    """Стартовая клавиатура бота."""
    return {
        "inline_keyboard": [
            [ {"text": "Рассчитать бодиграф", "web_app": {"url": WEBAPP_URL}} ],
            [ {"text": "Что с этим делать (видео)", "url": VIDEO_URL} ],
            [ {"text": "Рассчитать на сайте", "url": DIRECT_LINK} ],
        ]
    }

def build_redirect_url(base_url: str, payload: dict) -> str:
    """Собираем ссылку на human-design.space с параметрами и UTM."""
    parts = urlsplit(base_url)
    qs = parse_qs(parts.query, keep_blank_values=True)

    for k, v in FIXED_UTM.items():
        qs.setdefault(k, [v])

    for k, v in (payload or {}).items():
        if v is None:
            continue
        s = str(v).strip()
        if s:
            qs[k] = [s]

    new_query = urlencode(qs, doseq=True, encoding="utf-8", safe=" .-_:")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

# ---------- healthcheck
@app.get("/")
def health():
    return "OK"

# ---------- страница формы (передаём в шаблон базовую реф-ссылку)
@app.get("/hd")
def hd():
    return render_template("index.html", redirect_base=DIRECT_LINK)

# ---------- submit из БРАУЗЕРА: делаем 302-редирект на human-design.space
@app.post("/hd/submit")
def hd_submit():
    fd = request.form
    payload = {
        "name":   (fd.get("name")   or "").strip(),
        "gender": (fd.get("gender") or "").strip(),
        "date":   (fd.get("date")   or "").strip(),
        "time":   (fd.get("time")   or "").strip(),
        "city":   (fd.get("city")   or "").strip(),
    }
    link = build_redirect_url(DIRECT_LINK, payload)
    return redirect(link, code=302)

# ---------- поставить вебхук
@app.get("/set-webhook")
def set_webhook():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is empty"})
    webhook_url = f"{BASE_URL}/tg/webhook"
    r = requests.get(
        f"{TG_API}/setWebhook",
        params={"url": webhook_url, "secret_token": SECRET_TOKEN},
        timeout=10
    )
    try:
        return jsonify(r.json())
    except Exception:
        return r.text, r.status_code

# ---------- проверить состояние вебхука
@app.get("/get-webhook-info")
def get_webhook_info():
    r = requests.get(f"{TG_API}/getWebhookInfo", timeout=10)
    try:
        return jsonify(r.json())
    except Exception:
        return r.text, r.status_code

# ---------- приём апдейтов от Telegram
@app.post("/tg/webhook")
def webhook():
    # защита по секрету (должен совпадать с тем, что передавали в setWebhook)
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text") or ""

    # /start → высылаем клавиатуру
    if chat_id and text.startswith("/start"):
        tg("sendMessage",
           chat_id=chat_id,
           text=("Привет! Это помощник Sabina Energy по Human Design.\n\n"
                 "Нажми «Рассчитать бодиграф», заполни форму и получишь ссылку на расчёт."),
           reply_markup=build_keyboard())
        return "ok"

    # данные из Telegram WebApp (когда форму открывали из чата)
    web = msg.get("web_app_data")
    if chat_id and web:
        try:
            payload = json.loads(web.get("data") or "{}")
        except Exception:
            payload = {"raw": web.get("data")}
        link = build_redirect_url(DIRECT_LINK, payload)

        summary = (
            f"✅ Данные получены:\n"
            f"Имя: {payload.get('name','—')}\n"
            f"Пол: {payload.get('gender','—')}\n"
            f"Дата: {payload.get('date','—')}  Время: {payload.get('time','—')}\n"
            f"Город: {payload.get('city','—')}\n\n"
            f"Нажми кнопку, чтобы перейти к расчёту."
        )

        tg("sendMessage", chat_id=chat_id, text=summary,
           reply_markup={"inline_keyboard":[
               [ {"text":"Перейти к расчёту", "url": link} ],
               [ {"text":"Заполнить ещё раз", "web_app":{"url": WEBAPP_URL}} ]
           ]})
        return "ok"

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
