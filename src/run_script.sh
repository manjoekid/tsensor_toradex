#!/bin/bash

exec python3 ./src/test_serial.py --no-sandbox &
PYTHONPATH=`pwd`/src gunicorn --bind 0.0.0.0:5000 src.wsgi:app
