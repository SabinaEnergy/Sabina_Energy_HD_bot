import os
import requests
from flask import Flask, render_template

app = Flask(__name__, template_folder="webapp", static_folder="webapp/static", static_url_path="/static")

@app.get("/")
def health():
    return "OK"

@app.get("/hd")
def hd():
    return render_template("index.html")

# Маршрут для установки вебхука
@app.get("/set-webhook")
def set_webhook():
    bot_token = os.getenv("BOT_TOKEN")
    base_url = os.getenv("BASE_URL")
    secret_token = os.getenv("SECRET_TOKEN")
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    webhook_url = f"{base_url}/webhook"
    resp = requests.get(url, params={"url": webhook_url, "secret_token": secret_token})
    return resp.json()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
