#!/usr/bin/env bash

if [ $app = operator ]; then
  kopf run --verbose --standalone -A --log-format=full --liveness http://0.0.0.0:8080  main/np_operator.py
else
  nginx -g "daemon off;" &
  python3 main/np_webhook.py
fi