import os, json, requests
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qs
from flask import Flask, request, send_from_directory, jsonify, redirect
from dotenv import load_dotenv
load_dotenv()

# === НАСТРОЙКИ И ОКРУЖЕНИЕ ===
BOT_TOKEN         = os.getenv("BOT_TOKEN", "").strip()
BASE_URL          = os.getenv("BASE_URL", "https://sabina-energy-hd-bot.onrender.com").rstrip("/")
WEBAPP_URL        = os.getenv("WEBAPP_URL", f"{BASE_URL}/hd")
VIDEO_URL         = os.getenv("VIDEO_URL", "https://t.me/your_channel/123")
DIRECT_LINK       = os.getenv("DIRECT_LINK", "https://human-design.space")
SECRET_TOKEN      = os.getenv("SECRET_TOKEN", "SabinaSecret")

# --- BodyGraph API (заполнится когда возьмёшь ключ) ---
BG_API_KEY        = os.getenv("BODYGRAPH_API_KEY", "").strip()
BG_API_BASE       = os.getenv("BODYGRAPH_API_BASE", "https://api.bodygraphchart.com").rstrip("/")
# Эти два значения возьми из их документации (после входа): 
BG_CREATE_EP      = os.getenv("BG_CREATE_ENDPOINT", "/v1/charts")          # POST
BG_IMAGE_EP       = os.getenv("BG_IMAGE_ENDPOINT", "/v1/charts/{id}/image") # GET (PNG/SVG)
# -------------------------------------------------------

# Резервный редирект (если ключа нет)
FALLBACK_REDIRECT_BASE = os.getenv(
    "REDIRECT_BASE_URL",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/"
)

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__, static_folder="webapp", static_url_path="/hd")

def tg(method, **params):
    if not BOT_TOKEN:
        return None
    try:
        return requests.post(f"{TG_API}/{method}", json=params, timeout=15)
    except Exception:
        return None

def add_utm(url, extra: dict):
    """Подмешиваем UTM и переданные параметры в любой URL."""
    parts = urlsplit(url)
    qs = parse_qs(parts.query, keep_blank_values=True)

    # фиксированные utm
    qs.setdefault("utm_source", ["telegram"])
    qs.setdefault("utm_medium", ["bot"])
    qs.setdefault("utm_campaign", ["sabina_hd_bot"])

    # пользовательские
    for k, v in extra.items():
        if v is None or str(v).strip() == "":
            continue
        qs[k] = [str(v)]

    new_q = urlencode(qs, doseq=True, encoding="utf-8")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_q, parts.fragment))


# ============== СТАТИКА/ХЕЛСЧЕК ==============
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


# ============== TELEGRAM ==============
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
    return jsonify(r.json())

@app.post("/tg/webhook")
def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        return "forbidden", 403

    upd = request.get_json(silent=True) or {}
    msg = upd.get("message") or upd.get("edited_message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = msg.get("text")

    # приветствие
    if text and text.startswith("/start"):
        kb = {
            "inline_keyboard":[
                [ { "text":"Рассчитать бодиграф", "web_app": { "url": WEBAPP_URL } } ],
                [ { "text":"Рассчитать на сайте", "url": DIRECT_LINK } ]
            ]
        }
        tg("sendMessage",
           chat_id=chat_id,
           text="Привет! Это помощник Sabina Energy по Human Design.\nНажми «Рассчитать бодиграф»👇",
           reply_markup=kb)
        return "ok"

    # данные из WebApp
    web = msg.get("web_app_data")
    if web:
        try:
            payload = json.loads(web.get("data") or "{}")
        except Exception:
            payload = {"raw": web.get("data")}

        # 1) если есть API-ключ — пробуем вызывать BodyGraph
        if BG_API_KEY:
            try:
                bg = call_bodygraph_api(payload)
                image_url = bg.get("image_url")
                report_url = bg.get("report_url") or bg.get("url") or DIRECT_LINK

                # Картинка + кнопка
                if image_url:
                    tg("sendPhoto", chat_id=chat_id, photo=image_url,
                       caption="Твой бодиграф. Полный расчёт по кнопке ниже 👇",
                       reply_markup={"inline_keyboard":[
                           [ {"text":"Открыть полный отчёт", "url": report_url} ]
                       ]})
                else:
                    tg("sendMessage", chat_id=chat_id,
                       text=f"Готово! Отчёт по кнопке ниже.",
                       reply_markup={"inline_keyboard":[
                           [ {"text":"Открыть отчёт", "url": report_url} ]
                       ]})
                return "ok"
            except Exception as e:
                # Падаем в резервный редирект
                pass

        # 2) резерный переход на human-design.space с параметрами
        link = build_fallback_redirect(payload)
        tg("sendMessage", chat_id=chat_id,
           text="Открой расчёт по кнопке:",
           reply_markup={"inline_keyboard":[
               [ {"text":"Перейти к расчёту", "url": link} ],
               [ {"text":"Заполнить ещё раз", "web_app":{"url": WEBAPP_URL}} ]
           ]})
    return "ok"


# ============== REST API ДЛЯ ВЕБ-ФОРМЫ ==============
@app.post("/api/compute")
def compute():
    """Принимает JSON с полями формы. Если есть ключ — вызываем BodyGraph.
       Всегда возвращаем JSON { ok, report_url, image_url, fallback_url }.
    """
    data = request.get_json(silent=True) or {}
    # Если API-ключ настроен — основной путь
    if BG_API_KEY:
        try:
            res = call_bodygraph_api(data)
            return jsonify({"ok": True, **res})
        except Exception as e:
            # мягкий откат в резерв
            pass

    # резервный урл
    return jsonify({
        "ok": True,
        "report_url": build_fallback_redirect(data),
        "image_url": None,
        "fallback_url": build_fallback_redirect(data),
        "mode": "fallback"
    })


# ============== ИНТЕГРАЦИЯ С BODYGRAPH ==============
def call_bodygraph_api(payload: dict) -> dict:
    """
    ВНИМАНИЕ: эндпоинты и точные названия полей возьми из их документации
    (https://bodygraph.com/feature/human-design-api/ → ‘API documentation’).
    Здесь всё разнесено по переменным, чтобы ты просто подставила.
    """
    headers = {
        "Authorization": f"Bearer {BG_API_KEY}",
        "Content-Type": "application/json"
    }

    # Нормализация входных данных из формы
    # ожидаем: name, gender (male/female), date (ДД.ММ.ГГГГ), time (HH:MM),
    # city (строка), lat, lon, tz_offset (необяз.)
    name    = (payload.get("name") or "").strip()
    gender  = (payload.get("gender") or "").strip()   # "male" / "female"
    date    = (payload.get("date") or "").strip()     # "09.09.1990"
    time    = (payload.get("time") or "").strip()     # "15:30"
    city    = (payload.get("city") or "").strip()
    lat     = payload.get("lat")
    lon     = payload.get("lon")
    tz_off  = payload.get("tz_offset")  # например "+03:00"

    # Пример тела запроса (подгоняешь под их доку):
    body = {
        "name": name or "Client",
        "gender": gender or "female",
        "birth": {
            "date": date,            # ДД.ММ.ГГГГ или ГГГГ-ММ-ДД — как требует их API
            "time": time,            # HH:MM
            "city": city,
            "latitude": lat,
            "longitude": lon,
            "tz_offset": tz_off      # опционально
        },
        # можно добавлять локаль/язык, формат изображений и т.д. — см. их доки
        "options": {
            "image_format": "png",
            "include_report_url": True
        }
    }

    # 1) создаём чарт
    create_url = f"{BG_API_BASE}{BG_CREATE_EP}"
    r = requests.post(create_url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    j = r.json()

    # предположим, что API вернёт id/uuid и ссылки
    chart_id   = j.get("id") or j.get("chart_id")
    report_url = j.get("report_url") or j.get("public_url") or j.get("url")
    image_url  = j.get("image_url")

    # Если картинку нужно запросить отдельно:
    if not image_url and chart_id and "{id}" in BG_IMAGE_EP:
        img_url = f"{BG_API_BASE}{BG_IMAGE_EP.replace('{id}', str(chart_id))}"
        # Некоторые API отдают картинку сразу, некоторые — URL
        img_resp = requests.get(img_url, headers=headers, timeout=30)
        if img_resp.status_code == 200 and "image" in img_resp.headers.get("Content-Type",""):
            # заливаем куда-то CDN и отдаём URL (пропускаем для краткости)
            pass
        else:
            try:
                image_url = img_resp.json().get("image_url")
            except Exception:
                image_url = None

    # safety fallback — если не вернулся отчет
    if not report_url:
        report_url = DIRECT_LINK

    return {
        "report_url": report_url,
        "image_url": image_url,
        "chart_id": chart_id
    }


# ============== РЕЗЕРВНЫЙ РЕДИРЕКТ НА HUMAN-DESIGN.SPACE ==============
def build_fallback_redirect(payload: dict) -> str:
    """
    Мы не знаем глубокую ссылку human-design.space, которая сразу строит карту.
    Поэтому ведём на их страницу расчёта + передаём параметры в query для аналитики.
    Пользователь уже там повторно нажмёт «Рассчитать».
    """
    params = {
        "name":   payload.get("name"),
        "gender": payload.get("gender"),
        "date":   payload.get("date"),
        "time":   payload.get("time"),
        "city":   payload.get("city"),
        "rave":   request.args.get("rave") or os.getenv("RAVE_ID") or "7366406054640513",  # твой реф
    }
    return add_utm(FALLBACK_REDIRECT_BASE, params)


# ============== СЕРВЕР ==============
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
