import os
from flask import Flask, request, redirect, render_template_string

app = Flask(__name__)

REDIRECT_BASE_URL = os.getenv("REDIRECT_BASE_URL", "https://human-design.space/dizajn-cheloveka-raschet-karty/#/")

# Простая HTML-форма
FORM_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Калькулятор Human Design</title>
</head>
<body>
    <h2>Введите данные для расчёта Бодиграфа</h2>
    <form action="/calculate" method="get">
        Имя: <input type="text" name="name" required><br><br>
        Дата рождения: <input type="date" name="birth_date" required><br><br>
        Время рождения: <input type="time" name="birth_time" required><br><br>
        Место рождения: <input type="text" name="birth_place" required><br><br>
        <button type="submit">Рассчитать</button>
    </form>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(FORM_HTML)

@app.route("/calculate")
def calculate():
    name = request.args.get("name")
    birth_date = request.args.get("birth_date")
    birth_time = request.args.get("birth_time")
    birth_place = request.args.get("birth_place")

    # Конструктор ссылки (динамика)
    redirect_url = (
        f"{REDIRECT_BASE_URL}"
        f"?name={name}&date={birth_date}&time={birth_time}&place={birth_place}"
    )

    return redirect(redirect_url, code=302)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
