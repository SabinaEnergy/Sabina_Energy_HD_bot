from flask import Flask, render_template

app = Flask(__name__, template_folder="webapp")

@app.route("/")
def home():
    return "OK"

@app.route("/hd")
def hd_form():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
