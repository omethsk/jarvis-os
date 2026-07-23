#!/bin/bash
# Checks the Flask backend health endpoint and restarts the user service if unresponsive.
if curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:5000/ping | grep -q "^200$"; then
  exit 0
fi

echo "$(date): jarvis backend unresponsive, restarting jarvis.service"
systemctl --user restart jarvis.service
sleep 5

if curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:5000/ping | grep -q "^200$"; then
  echo "$(date): recovery successful"
else
  echo "$(date): recovery FAILED, backend still unresponsive"
fi
