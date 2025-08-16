import os
from flask import Flask, request, jsonify, redirect, Markup

from urllib.parse import urlsplit, urlunsplit, urlencode

app = Flask(__name__)

# ========= КОНСТАНТЫ =========
# Страница калькулятора со SPA/hash-роутером
DIRECT_LINK = os.getenv(
    "DIRECT_LINK",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/"
)
# Твоя рефка
RAVE_CODE = os.getenv("RAVE_CODE", "7366406054640513")


# ========= ХЕЛПЕР: сборка конечной ссылки =========
def build_redirect_url(base_url: str, payload: dict) -> str:
    """
    Собираем ссылку для редиректа на human-design.space.
    Т.к. у них hash-роутер, параметры должны быть ПОСЛЕ '#/'.

    Всегда добавляем:
      - rave=<твой_код>

    Также добавляем все поля формы (name, gender, date, time, city)
    — пока цель их игнорирует, но они будут видны в адресе.
    Если когда-нибудь появится report_hash — добавим его и попадём сразу в готовый отчёт.
    """
    base = base_url or DIRECT_LINK
    parts = urlsplit(base)

    # Что положим в hash-часть
    h = {
        "rave": RAVE_CODE,
    }

    # Перекладываем поля формы (если есть)
    # НАЗВАНИЯ ключей можно будет поменять под формат deep-link, когда дадут.
    for k in ("name", "gender", "date", "time", "city", "report_hash"):
        v = (payload or {}).get(k)
        if v:
            h[k] = str(v).strip()

    # Кодируем параметры для части ПОСЛЕ "#/"
    hq = urlencode(h, doseq=True, encoding="utf-8", safe=" .-_:")
    # Возвращаем строку вида: scheme://netloc/path#/?<hq>
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, "/?" + hq))


# ========= ТЕСТ =========
@app.get("/ping")
def ping():
    return jsonify({"status": "ok"})


# ========= ФОРМА =========
@app.get("/hd")
def hd_form():
    # Минимальный HTML прямо из кода, чтобы ничего больше не менять
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Расчёт бодиграфа</title>
<style>
  body {{
    margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    background: linear-gradient(135deg,#ff7746,#ff9d3f);
    min-height:100vh; display:flex; align-items:center; justify-content:center; color:#fff;
  }}
  .card {{
    width: min(680px, 92vw);
    background: rgba(0,0,0,.35);
    border-radius: 16px; padding: 22px 20px 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,.25);
  }}
  h1 {{ font-size: 24px; margin: 0 0 14px; text-align:center; }}
  form {{
    display:grid; gap:12px;
    grid-template-columns: 1fr 1fr;
  }}
  .row-1 {{ grid-column: 1 / -1; }}
  input, select {{
    width:100%; padding:12px 14px; border-radius:12px; border:0; outline:0;
    background: rgba(255,255,255,.92); color:#1b1b1b; font-size:16px;
  }}
  button {{
    grid-column: 1 / -1;
    padding:14px 18px; font-size:17px; border-radius:12px; border:0; cursor:pointer;
    background:#ff5a43; color:#fff; font-weight:600;
  }}
  .hint {{ grid-column:1 / -1; opacity:.85; font-size:13px; text-align:center; }}
</style>
</head>
<body>
  <div class="card">
    <h1>Твоя карта Human Design</h1>
    <form method="post" action="/redirect">
      <input class="row-1" type="text" name="name"   placeholder="Имя" required />
      <select name="gender" required>
        <option value="" hidden>Пол</option>
        <option value="Жен">Жен</option>
        <option value="Муж">Муж</option>
      </select>
      <input type="date"  name="date"  placeholder="Дата рождения" required />
      <input type="time"  name="time"  placeholder="Время рождения" required />
      <input class="row-1" type="text" name="city"   placeholder="Город рождения" required />
      <div class="hint">После отправки вы перейдёте на human-design.space по вашей реф-ссылке.</div>
      <button type="submit">Рассчитать</button>
    </form>
  </div>
</body>
</html>
    """
    return Markup(html)


# ========= РЕДИРЕКТ =========
@app.route("/redirect", methods=["GET", "POST"])
def redirect_to_hd():
    # Забираем данные и из GET, и из POST
    payload = {}
    for k in ("name", "gender", "date", "time", "city", "report_hash"):
        payload[k] = request.values.get(k, "").strip()

    url = build_redirect_url(DIRECT_LINK, payload)
    return redirect(url, code=302)


# ========= ЗАПУСК =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
