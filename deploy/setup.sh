#!/usr/bin/env bash
# One-shot provisioning for a fresh Linux VM (Ubuntu OR Oracle Linux / RHEL).
# Auto-detects the package manager and the login user, and generates systemd
# unit files with the correct user + paths. Run from the repo root:
#     bash deploy/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

REPO_DIR="$(pwd)"
RUN_USER="$(whoami)"

echo "==> Installing system packages"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y python3 python3-venv python3-pip git
  PYBIN=python3
elif command -v dnf >/dev/null 2>&1; then
  # Oracle Linux / RHEL / Fedora. Prefer Python 3.11 for modern syntax.
  sudo dnf install -y python3.11 python3.11-pip git || sudo dnf install -y python3 python3-pip git
  if command -v python3.11 >/dev/null 2>&1; then PYBIN=python3.11; else PYBIN=python3; fi
else
  echo "!! No apt-get or dnf found. Install Python 3.11+, pip, and git manually." >&2
  exit 1
fi
echo "==> Using interpreter: $PYBIN ($($PYBIN --version 2>&1))"

echo "==> Creating virtualenv + installing deps"
$PYBIN -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  echo "==> Creating .env from template (edit it before going live)"
  cp .env.example .env
fi

chmod +x deploy/retune.sh

echo "==> Generating systemd unit files for user '$RUN_USER' at '$REPO_DIR'"
cat > deploy/cryptoking.service <<EOF
[Unit]
Description=CryptoKing trading bot (web dashboard + engine)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${REPO_DIR}
EnvironmentFile=${REPO_DIR}/.env
ExecStart=${REPO_DIR}/.venv/bin/python webapp.py --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > deploy/cryptoking-learn.service <<EOF
[Unit]
Description=CryptoKing self-learning re-tune (fetch candles + walk-forward)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${RUN_USER}
WorkingDirectory=${REPO_DIR}
EnvironmentFile=${REPO_DIR}/.env
ExecStart=${REPO_DIR}/deploy/retune.sh
EOF

cat <<EOF

==> Done. Next steps:

1. Edit .env  (MODE=paper to start; add API keys only for live).
       nano .env

2. Test it runs:
       .venv/bin/python webapp.py --host 127.0.0.1 --port 8000
   then Ctrl-C.

3. Install the systemd services (runs 24/7, restarts on crash/reboot):
       sudo cp deploy/cryptoking.service /etc/systemd/system/
       sudo cp deploy/cryptoking-learn.service /etc/systemd/system/
       sudo cp deploy/cryptoking-learn.timer  /etc/systemd/system/
       sudo systemctl daemon-reload
       sudo systemctl enable --now cryptoking.service
       sudo systemctl enable --now cryptoking-learn.timer

4. View the dashboard from your laptop via SSH tunnel (use your login user):
       ssh -i <key> -L 8000:localhost:8000 ${RUN_USER}@<VM_PUBLIC_IP>
   then open http://localhost:8000

5. Logs:
       journalctl -u cryptoking -f
EOF
