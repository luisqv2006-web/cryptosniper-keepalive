# ------------------------------------
# CRYPTOSNIPER FX — CORE BOT
# Conexión WebSocket + Telegram /status
# ------------------------------------

from keep_alive import keep_alive
keep_alive()

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import websocket
import json
import time
import threading

# ==============================
# CONFIGURACIÓN — TOKENS
# ==============================
DERIV_TOKEN = "lit3a706U07EYMV"  # Token real Deriv
ACCOUNT_ID = "CR9890525"

TELEGRAM_TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = -1003348348510  # Canal donde responde

ws = None
connected = False


# ==============================
# FUNCIÓN DE CONEXIÓN A DERIV
# ==============================
def connect_deriv():
    global ws, connected
    ws = websocket.WebSocket()
    ws.connect("wss://ws.deriv.com/websockets/v3?app_id=1089")
    connected = True
    
    # Autorizar con token real
    auth = { "authorize": DERIV_TOKEN }
    ws.send(json.dumps(auth))
    
    print("🔥 [DerivAPI] Conectado y autorizado")


# ==============================
# ESCUCHAR RESPUESTAS DE DERIV
# ==============================
def listen_deriv():
    global ws, connected
    while True:
        try:
            msg = ws.recv()
            print("[Deriv] >>", msg)
        except:
            print("[Deriv] ❌ Desconectado, reconectando...")
            connected = False
            connect_deriv()
            time.sleep(3)


# ==============================
# COMANDO: /status
# ==============================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    
    estado = "🟢 Conectado a Deriv" if connected else "🔴 No conectado"
    await context.bot.send_message(chat_id=CHAT_ID, text=f"📡 Estado del bot:\n{estado}")


# ==============================
# INICIAR BOT DE TELEGRAM
# ==============================
def start_telegram():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("status", status))

    print("🤖 Telegram escuchando...")
    app.run_polling()


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    connect_deriv()

    threading.Thread(target=listen_deriv).start()
    
    start_telegram()
