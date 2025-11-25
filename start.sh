#!/bin/bash

echo "🚀 Iniciando CryptoSniper FX con reinicio automático..."

while true
do
    python3 main.py
    echo "⚠️ Bot detenido — Reiniciando en 3 segundos..."
    sleep 3
done
