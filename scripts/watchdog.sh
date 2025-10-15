#!/usr/bin/env bash
URL="http://127.0.0.1:5000/api/v1/status"
if ! curl -s --max-time 3 "$URL" >/dev/null; then
  echo "[watchdog] restart plantai.service"
  sudo systemctl restart plantai.service
fi
