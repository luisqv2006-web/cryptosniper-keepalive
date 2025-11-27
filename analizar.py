import random

def analizar_mercado(par):
    """
    Simula análisis técnico real.
    Aquí luego podemos meter RSI, EMA, Velas, etc.
    """

    probabilidad = random.randint(1, 100)

    if probabilidad > 70:
        direccion = random.choice(["CALL", "PUT"])
        confianza = probabilidad
        return direccion, confianza

    return None
