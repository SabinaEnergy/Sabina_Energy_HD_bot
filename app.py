import os
from flask import Flask, render_template, send_from_directory

# шаблоны лежат в webapp, статика в webapp/static, а у статики URL будет /static
app = Flask(__name__, template_folder="webapp", static_folder="webapp/static", static_url_path="/static")

@app.get("/")
def health():
    return "OK"

# страница /hd
@app.get("/hd")
def hd():
    return render_template("index.html")

# (опционально) если хочешь раздавать любые файлы из webapp по /hd/...
@app.get("/hd/<path:fname>")
def hd_files(fname):
    return send_from_directory("webapp", fname)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
