#!/usr/bin/env bash

if [ $app = operator ]; then
  kopf run --standalone -A --log-format=full --liveness http://0.0.0.0:8080  main/np_operator.py
else
  nginx -g "daemon off;" &
  nohup tools/monitor-crt.sh &
  python3 main/np_webhook.py
fi