#!/bin/bash

# Arrancar Flask con Gunicorn (producción real)
gunicorn -b 0.0.0.0:$PORT main:app
