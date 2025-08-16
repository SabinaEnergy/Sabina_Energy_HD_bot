# app.py — универсально: Telegram + браузер (редирект на human-design.space)
import os
import json
import requests
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from flask import Flask, render_template, request, jsonify, redirect

app = Flask(
    __name__,
    template_folder="webapp",          # HTML-шаблоны
    static_folder="webapp/static",     # статика (CSS/JS/картинки)
    static_url_path="/static"
)

# ===================== ENV =====================
# Render: Settings → Environment
BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
BASE_URL     = os.getenv("BASE_URL", "https://sabina-energy-hd-bot.onrender.com")
WEBAPP_URL   = os.getenv("WEBAPP_URL", f"{BASE_URL}/hd")
# БАЗОВАЯ точка сайта с hash-роутером:
DIRECT_LINK  = os.getenv("DIRECT_LINK", "https://human-design.space/#/")
# Твой реф-код
RAVE_CODE    = os.getenv("RAVE_CODE", "7366406054640513")
VIDEO_URL    = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SabinaSecret")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# UTM для трекинга (используем только для сообщений, в ссылку с hash добавлять не обязательно)
FIXED_UTM = {
    "utm_source": "telegram",
    "utm_medium": "bot",
    "utm_campaign": "sabina_hd_bot",
}


# ===================== helpers =====================
def tg(method, **params):
    return requests.post(f"{TG_API}/{method}", json=params, timeout=10)


def build_keyboard():
    return {
        "inline_keyboard": [
            [ {"text": "Рассчитать бодиграф", "web_app": {"url": WEBAPP_URL}} ],
            [ {"text": "Что с этим делать (видео)", "url": VIDEO_URL} ],
            [ {"text": "Рассчитать на сайте", "url": DIRECT_LINK + f"?rave={RAVE_CODE}"} ],
        ]
    }


def build_redirect_url(base_url: str, payload: dict) -> str:
    """
    Собираем ссылку формата:
      https://human-design.space/#/?rave=<RAVE_CODE>            (всегда)
      + &report_hash=...                                        (если передан)
    Другие поля (имя/дата/время/город) сайт по ссылке НЕ понимает.
    """
    base = base_url or "https://human-design.space/#/"
    parts = urlsplit(base)

    # что будет в части ПОСЛЕ "#/"
    hash_query = {"rave": RAVE_CODE}

    # если нам как-то передали готовый report_hash — добавим
    rh = (payload or {}).get("report_hash")
    if rh and str(rh).strip():
        hash_query["report_hash"] = str(rh).strip()

    # собираем query после "#/?"
    hq = urlencode(hash_query, doseq=True, encoding="utf-8", safe=" .-_:")
    # возвращаем строку вида: scheme://netloc/path#/?<hq>
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, "/?" + hq))


# ===================== routes =====================
@app.get("/")
def health():
    return "OK"


@app.get("/hd")
def hd():
    # передадим базовую ссылку в шаблон (используется JS)
    return render_template("index.html", redirect_base=DIRECT_LINK)


# БРАУЗЕРНЫЙ submit: сервер делает 302-редирект на human-design.space
@app.post("/hd/submit")
def hd_submit():
    fd = request.form
    payload = {
        "name":   (fd.get("name")   or "").strip(),
        "gender": (fd.get("gender") or "").strip(),
        "date":   (fd.get("date")   or "").strip(),
        "time":   (fd.get("time")   or "").strip(),
        "city":   (fd.get("city")   or "").strip(),
        # Если когда-нибудь будет возможность получать report_hash из API — положим сюда:
        "report_hash": (fd.get("report_hash") or "").strip(),
    }
    link = build_redirect_url(DIRECT_LINK, payload)
    return redirect(link, code=302)


# Поставить вебхук у Telegram
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


# Проверить состояние вебхука
@app.get("/get-webhook-info")
def get_webhook_info():
    r = requests.get(f"{TG_API}/getWebhookInfo", timeout=10)
    try:
        return jsonify(r.json())
    except Exception:
        return r.text, r.status_code


# Приём апдейтов от Telegram
@app.post("/tg/webhook")
def webhook():
    # защита секретом
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text") or ""

    # /start → отправим клавиатуру
    if chat_id and text.startswith("/start"):
        tg("sendMessage",
           chat_id=chat_id,
           text=("Привет! Это помощник Sabina Energy по Human Design.\n\n"
                 "Нажми «Рассчитать бодиграф», заполни форму и получишь ссылку на расчёт."),
           reply_markup=build_keyboard())
        return "ok"

    # данные из Telegram WebApp (form → tg.sendData)
    web = msg.get("web_app_data")
    if chat_id and web:
        try:
            payload = json.loads(web.get("data") or "{}")
        except Exception:
            payload = {"raw": web.get("data")}

        link = build_redirect_url(DIRECT_LINK, payload)

        # текст-резюме + кнопка на расчёт
        summary = (
            f"✅ Данные получены:\n"
            f"Имя: {payload.get('name','—')}\n"
            f"Пол: {payload.get('gender','—')}\n"
            f"Дата: {payload.get('date','—')}  Время: {payload.get('time','—')}\n"
            f"Город: {payload.get('city','—')}\n\n"
            f"Нажми кнопку, чтобы перейти к расчёту."
        )

        tg("sendMessage", chat_id=chat_id, text=summary,
           reply_markup={"inline_keyboard": [
               [ {"text": "Перейти к расчёту", "url": link} ],
               [ {"text": "Заполнить ещё раз", "web_app": {"url": WEBAPP_URL}} ]
           ]})
        return "ok"

    return "ok"


if __name__ == "__main__":
    # Render прокидывает порт в переменной окружения PORT
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
