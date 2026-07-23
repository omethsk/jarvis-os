#!/bin/bash
# Checks real connectivity (not just nmcli state) and recovers WiFi if down.
GATEWAY="192.168.1.1"

if ping -c 2 -W 3 "$GATEWAY" > /dev/null 2>&1; then
  exit 0
fi

echo "$(date): gateway unreachable, attempting recovery"

STATE=$(nmcli -t -f DEVICE,STATE device status | grep "^wlan0:" | cut -d: -f2)
echo "$(date): wlan0 state = $STATE"

if [ "$STATE" != "connected" ]; then
  sudo -n nmcli connection up "IOAS_Plus" 2>&1 || sudo -n nmcli connection up "IOAS_Plus_5G" 2>&1
  sleep 5
fi

if ! ping -c 2 -W 3 "$GATEWAY" > /dev/null 2>&1; then
  echo "$(date): still unreachable after reconnect attempt, restarting NetworkManager"
  sudo -n systemctl restart NetworkManager
  sleep 10
fi

if ping -c 2 -W 3 "$GATEWAY" > /dev/null 2>&1; then
  echo "$(date): recovery successful"
else
  echo "$(date): recovery FAILED, still unreachable"
fi
