from flask import Flask
from threading import Thread
import os
import subprocess

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and monitoring Deriv!"

def run():
    port = int(os.environ.get("PORT", 10000))
    # Use gunicorn as production server
    subprocess.run(['gunicorn', 'keep_alive:app', '-b', f'0.0.0.0:{port}'])

def keep_alive():
    t = Thread(target=run)
    t.start()
