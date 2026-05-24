from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return {"status": "ok", "message": "Bot dashboard running"}

def run():
    app.run(host="0.0.0.0", port=5000, debug=False)
