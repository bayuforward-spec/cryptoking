#!/usr/bin/env bash
# One-shot provisioning for an Ubuntu VM (e.g. Oracle Cloud Always Free).
# Run from the repo root after cloning: bash deploy/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Installing system packages"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git

echo "==> Creating virtualenv + installing deps"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
  echo "==> Creating .env from template (edit it before going live)"
  cp .env.example .env
fi

chmod +x deploy/retune.sh

cat <<'EOF'

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

4. View the dashboard from your laptop via SSH tunnel:
       ssh -L 8000:localhost:8000 ubuntu@<VM_PUBLIC_IP>
   then open http://localhost:8000

5. Logs:
       journalctl -u cryptoking -f

If your VM user isn't "ubuntu", edit the User= and paths in the .service files.
EOF
