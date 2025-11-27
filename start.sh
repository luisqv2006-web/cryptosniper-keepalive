#!/bin/bash
python3 main.py & 
gunicorn keep_alive:app --bind 0.0.0.0:$PORT
