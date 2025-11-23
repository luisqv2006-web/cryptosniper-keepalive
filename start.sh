#!/bin/bash

echo "🔁 Iniciando bot con reinicio automático..."

while true
do
  python3 main.py
  echo "⚠ Bot se detuvo — Reiniciando en 3 segundos..."
  sleep 3
done
