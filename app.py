import os
import requests
from urllib.parse import urlencode
from flask import Flask, request, redirect, render_template_string, jsonify

# -----------------------------
# ENV
# -----------------------------
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")                    # токен из @BotFather
BASE_URL        = os.getenv("BASE_URL", "https://example.com")  # https://<твой_сабдомен>.onrender.com
WEBAPP_URL      = os.getenv("WEBAPP_URL", f"{BASE_URL}/hd")     # https://<твой_сабдомен>.onrender.com/hd
SECRET_TOKEN    = os.getenv("SECRET_TOKEN", "SabinaSecret2025")

# Куда ведём пользователя (фолбэк, если нет провайдера API):
FALLBACK_URL    = os.getenv("REDIRECT_BASE_URL",
                            "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")
RAVE_CODE       = os.getenv("RAVE_CODE", "7366406054640513")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

# -----------------------------
# HTML-форма (встроенная)
# -----------------------------
FORM_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Расчёт бодиграфа</title>
  <style>
    :root{--bg1:#ff8c5a;--bg2:#d64b7c}
    *{box-sizing:border-box}
    body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Ubuntu,"Helvetica Neue",Arial}
    .wrap{min-height:100svh;display:flex;align-items:center;justify-content:center;background:linear-gradient(180deg,var(--bg1),var(--bg2))}
    .card{width:min(720px,92vw);background:#0f1222cc;color:#fff;border-radius:16px;padding:24px 20px;backdrop-filter:blur(6px)}
    h1{margin:0 0 10px;font-size:28px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .grid .full{grid-column:1/-1}
    label{font-size:13px;opacity:.9}
    input,select{width:100%;padding:12px;margin-top:6px;border-radius:10px;border:1px solid #ffffff33;background:#0b0e1a;color:#fff}
    button{margin-top:16px;width:100%;padding:14px;border:none;border-radius:12px;font-weight:600;font-size:15px;background:linear-gradient(90deg,#ff6a3d,#ffb547);color:#1a0d00;cursor:pointer}
    .hint{margin-top:8px;font-size:12px;opacity:.85;text-align:center}
  </style>
</head>
<body>
  <div class="wrap">
    <form class="card" id="form" action="/redirect" method="post">
      <h1>Твоя карта Human Design</h1>
      <div class="grid">
        <div>
          <label>Имя</label>
          <input name="name" placeholder="Например, Анна" required/>
        </div>
        <div>
          <label>Пол</label>
          <select name="gender">
            <option value="female">Жен</option>
            <option value="male">Муж</option>
          </select>
        </div>
        <div>
          <label>Дата рождения</label>
          <input name="date" type="date" required/>
        </div>
        <div>
          <label>Время рождения</label>
          <input name="time" type="time" required/>
        </div>
        <div class="full">
          <label>Город рождения</label>
          <input name="city" placeholder="Начните вводить город" required/>
        </div>
      </div>
      <button type="submit" id="btn">Рассчитать</button>
      <div class="hint">После отправки откроется расчёт на human-design.space</div>
    </form>
  </div>
  <script>
    // Небольшой UX: блокируем кнопку на время отправки
    const form = document.getElementById('form');
    const btn  = document.getElementById('btn');
    form.addEventListener('submit', () => {
      btn.disabled = true;
      btn.textContent = 'Отправляем...';
    });
  </script>
</body>
</html>
"""

# -----------------------------
# Утилиты
# -----------------------------
def tg(method, **params):
    if not BOT_TOKEN:
        return None
    try:
        return requests.post(f"{TG_API}/{method}", json=params, timeout=10)
    except requests.RequestException:
        return None

def build_fallback_url(name, date, time_, city, gender):
    # Пробрасываем все поля + UTM и твой реф-код
    q = {
        "rave": RAVE_CODE,
        "name": name,
        "date": date,
        "time": time_,
        "city": city,
        "gender": gender,
        "utm_source": "telegram-bot",
        "utm_medium": "webapp",
        "utm_campaign": "sabina_hd_bot"
    }
    return f"{FALLBACK_URL}?{urlencode(q)}"

def start_keyboard():
    # Кнопка WebApp + 2 обычные ссылки
    return {
        "inline_keyboard":[
            [ { "text":"Рассчитать бодиграф", "web_app": { "url": WEBAPP_URL } } ],
            [ { "text":"Рассчитать на сайте", "url": FALLBACK_URL } ]
        ]
    }

# -----------------------------
# HTTP-маршруты
# -----------------------------
@app.get("/")
def health():
    return "OK"

@app.get("/hd")
def show_form():
    return render_template_string(FORM_HTML)

@app.post("/redirect")
def form_redirect():
    # Берём данные из формы
    name   = (request.form.get("name") or "").strip()
    date   = (request.form.get("date") or "").strip()    # YYYY-MM-DD
    time_  = (request.form.get("time") or "").strip()    # HH:MM
    city   = (request.form.get("city") or "").strip()
    gender = (request.form.get("gender") or "female").strip()

    # Пока deep-link у human-design.space недоступен — делаем фолбэк с параметрами
    url = build_fallback_url(name, date, time_, city, gender)
    return redirect(url, code=302)

# -----------------------------
# Telegram: настройка вебхука
# -----------------------------
@app.get("/set-webhook")
def set_webhook():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is empty"})
    url = f"{BASE_URL}/tg/webhook"
    try:
        r = requests.get(
            f"{TG_API}/setWebhook",
            params={"url": url, "secret_token": SECRET_TOKEN},
            timeout=10
        )
        return jsonify(r.json())
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/get-webhook-info")
def get_webhook_info():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is empty"})
    try:
        r = requests.get(f"{TG_API}/getWebhookInfo", timeout=10)
        return jsonify(r.json())
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# -----------------------------
# Telegram: обработчик вебхука
# -----------------------------
@app.post("/tg/webhook")
def tg_webhook():
    # Проверяем секрет (если поставили при setWebhook)
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message") or {}

    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()

    # /start → отправляем привет и кнопку WebApp
    if text.startswith("/start"):
        tg("sendMessage",
           chat_id=chat_id,
           text="Привет! Это помощник Sabina Energy по Human Design.\nНажми «Рассчитать бодиграф»👇",
           reply_markup=start_keyboard())
        return "ok"

    # Любое другое сообщение — подсказываем кнопку
    if chat_id:
        tg("sendMessage",
           chat_id=chat_id,
           text="Нажми «Рассчитать бодиграф», чтобы открыть форму.",
           reply_markup=start_keyboard())

    return "ok"

# -----------------------------
# Run (локально)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
