import os, json, requests
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from flask import Flask, request, send_from_directory, jsonify
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL", "https://sabina.coach")
WEBAPP_URL = os.getenv("WEBAPP_URL", f"{BASE_URL}/hd")
VIDEO_URL = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
DIRECT_LINK = os.getenv("DIRECT_LINK")
REDIRECT_BASE_URL = os.getenv("REDIRECT_BASE_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SabinaSecret")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__, static_folder="webapp", static_url_path="/hd")

def tg(method, **params):
    return requests.post(f"{TG_API}/{method}", json=params, timeout=10)

def build_keyboard():
    return {
        "inline_keyboard":[
            [ { "text":"Рассчитать бодиграф", "web_app": { "url": WEBAPP_URL } } ],
            [ { "text":"Что с этим делать (видео)", "url": VIDEO_URL } ],
            [ { "text":"Рассчитать на сайте", "url": DIRECT_LINK } ]
        ]
    }

FIXED_UTM = {
    "utm_source":"telegram",
    "utm_medium":"bot",
    "utm_campaign":"sabina_hd_bot"
}

def build_redirect_url(payload: dict) -> str:
    parts = urlsplit(REDIRECT_BASE_URL)
    qs = parse_qs(parts.query, keep_blank_values=True)
    for k,v in FIXED_UTM.items():
        qs.setdefault(k, [v])
    for k, v in payload.items():
        if v is None or str(v).strip() == "":
            continue
        qs[k] = [str(v)]
    new_query = urlencode(qs, doseq=True, encoding="utf-8", safe=" .-_:")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

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

@app.get("/set-webhook")
def set_webhook():
    url = f"{BASE_URL}/tg/webhook"
    r = requests.get(
        f"{TG_API}/setWebhook",
        params={"url": url, "secret_token": SECRET_TOKEN},
        timeout=10
    )
    return jsonify(r.json())

@app.post("/tg/webhook")
def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text")

    if text and text.startswith("/start"):
        tg("sendMessage",
           chat_id=chat_id,
           text="Привет! Это помощник Sabina Energy по Human Design.\nНажми «Рассчитать бодиграф»👇",
           reply_markup=build_keyboard())
        return "ok"

    web = msg.get("web_app_data")
    if web:
        try:
            payload = json.loads(web.get("data") or "{}")
        except Exception:
            payload = {"raw": web.get("data")}

        link = build_redirect_url(payload)

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
               [ {"text":"Ещё раз заполнить", "web_app":{"url": WEBAPP_URL}} ]
           ]})
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
