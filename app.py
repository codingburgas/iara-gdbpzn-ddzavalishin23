from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/templates/SignIn')
def SignIn():
    return "<h1>Sign In page</h1><p>This is where the sign‑in form would be.</p>"


@app.route('/templates/SignUp')
def SignUp():
    return "<h1>Sign Up page</h1><p>This is where the sign‑up form would be.</p>"


if __name__ == '__main__':
    app.run(debug=True)
