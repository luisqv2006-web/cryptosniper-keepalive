import random

def generar_senal(symbol):
    # TEMP: señal aleatoria con probabilidad baja
    # Luego la cambiamos a RSI real
    chance = random.randint(1, 20)

    if chance == 1:
        return "BUY"
    elif chance == 2:
        return "SELL"
    else:
        return None
