import os
from flask import Flask, render_template
from config import default


app = Flask(__name__)
app.config.from_object(default)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/canvas')
def canvas():
    return render_template('canvas.html')


def main():  
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()