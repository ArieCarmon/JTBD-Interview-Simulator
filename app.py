from flask import Flask, render_template

app = Flask(__name__)

## Home route
@app.route('/')
def home():
    return render_template('welcome.html')

## Options selection route
@app.route('/mode')
def options():
    return render_template('options.html')

if __name__ == '__main__':
    app.run(debug=True)
