from flask import Flask, send_from_directory
import os

app = Flask(__name__, static_folder="webapp", static_url_path="/hd")

@app.get("/")
def index():
    return "OK"

@app.get("/hd")
def webapp_index():
    return send_from_directory("webapp", "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

