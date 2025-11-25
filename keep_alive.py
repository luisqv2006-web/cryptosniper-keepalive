from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "CryptoSniper FX Running"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()
