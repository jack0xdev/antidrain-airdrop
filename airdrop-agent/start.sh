#!/usr/bin/env bash
set -euo pipefail
: "${VNC_PASSWORD:?Set VNC_PASSWORD in .env}"

Xvfb :99 -screen 0 1440x900x24 -nolisten tcp &
sleep 1
fluxbox >/dev/null 2>&1 &

mkdir -p ~/.vnc
x11vnc -storepasswd "$VNC_PASSWORD" ~/.vnc/passwd >/dev/null
x11vnc -display :99 -rfbauth ~/.vnc/passwd -forever -shared -rfbport 5900 -localhost -quiet &
websockify --web /usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &

[ -f /data/profile.yaml ] || cp /app/examples/profile.example.yaml /data/profile.yaml
[ -f /data/tasks.yaml ] || cp /app/examples/tasks.example.yaml /data/tasks.yaml

exec python -m agent.main
