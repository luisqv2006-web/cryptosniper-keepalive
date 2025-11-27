import requests
import os

DERIV_TOKEN = os.getenv("DERIV_TOKEN")

def ejecutar_operacion(par, direccion):
    print(f"🤖 Operando en DERIV → {par} | {direccion}")

    # Aquí después conectamos la orden real
    return True
