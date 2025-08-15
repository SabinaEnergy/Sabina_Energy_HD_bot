from flask import Flask, render_template

app = Flask(__name__, static_folder='webapp/static', template_folder='webapp')

@app.route('/hd')
def hd():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
