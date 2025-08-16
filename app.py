import os
from flask import Flask, request, jsonify, redirect
from urllib.parse import urlsplit, urlunsplit, urlencode

app = Flask(__name__)

# === Константы для Human Design ===
DIRECT_LINK = os.getenv(
    "DIRECT_LINK",
    "https://human-design.space/dizajn-cheloveka-raschet-karty/#/"
)
RAVE_CODE = os.getenv("RAVE_CODE", "7366406054640513")


# === Функция сборки ссылки ===
def build_redirect_url(base_url: str, payload: dict) -> str:
    """
    Собираем финальную ссылку для human-design.space.
    Пример:
    https://human-design.space/dizajn-cheloveka-raschet-karty/#/?rave=7366406054640513
    """
    base = base_url or DIRECT_LINK
    parts = urlsplit(base)

    # параметры для передачи в hash-части
    hash_query = {"rave": RAVE_CODE}

    # если когда-то будет report_hash
    rh = (payload or {}).get("report_hash")
    if rh and str(rh).strip():
        hash_query["report_hash"] = str(rh).strip()

    hq = urlencode(hash_query, doseq=True, encoding="utf-8", safe=" .-_:")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, "/?" + hq))


# === Тестовый маршрут для проверки работы сервера ===
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "message": "Сервер работает"})


# === Редирект на Human Design с параметрами ===
@app.route("/redirect", methods=["GET"])
def redirect_to_hd():
    """
    Пример запроса:
    http://localhost:5000/redirect
    -> перебросит на human-design.space с твоим ref-кодом
    """
    paylo
