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
    # Gunicorn como servidor WSGI de producción (sin warnings)
    subprocess.run([
        'gunicorn',
        'keep_alive:app',          # módulo:objeto Flask
        '-b', f'0.0.0.0:{port}',   # bind
        '--log-level', 'warning'   # solo muestra avisos importantes (opcional)
    ])

def keep_alive():
    t = Thread(target=run)
    t.start()
