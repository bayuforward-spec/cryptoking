# Deploying CryptoKing on Oracle Cloud (Always Free)

A step-by-step guide to run the bot 24/7 on a **free** Oracle Cloud VM — no VPS
bill, no hardware. The dashboard stays private (localhost + SSH tunnel) and the
bot restarts automatically on crash or reboot.

> Start in **paper mode**. Only switch to live after the backtester + paper
> results show a positive edge, and only with money you can afford to lose.
> Check local regulations (in Indonesia: Bappebti / OJK).

---

## 1. Create a free VM

1. Sign up at <https://www.oracle.com/cloud/free/> (Always Free includes VMs that
   run forever at no cost).
2. **Create a Compute instance**:
   - Image: **Ubuntu 22.04** (or newer).
   - Shape: an **Always Free–eligible** shape — `VM.Standard.E2.1.Micro` (x86) or
     `VM.Standard.A1.Flex` (ARM, up to 4 OCPU / 24 GB free). Either is plenty.
   - Add your SSH public key (or let Oracle generate a keypair and download it).
3. Note the instance's **public IP**.
4. Networking: you do **not** need to open any inbound port except SSH (22). The
   dashboard is reached through an SSH tunnel, so leave it off the public internet.

## 2. Connect and clone

Use the **username Oracle shows on the instance page** — `ubuntu` for an Ubuntu
image, `opc` for an Oracle Linux image:

```bash
ssh -i <your-key.key> <ubuntu|opc>@<VM_PUBLIC_IP>
git clone https://github.com/bayuforward-spec/cryptoking.git
cd cryptoking
git checkout claude/crypto-trading-bot-cy5qq2
```

`deploy/setup.sh` auto-detects the OS (apt/dnf) and generates the systemd units
for your login user — it works on both Ubuntu and Oracle Linux.

## 3. One-command setup

```bash
bash deploy/setup.sh
```

This installs Python, creates a virtualenv, installs dependencies, and copies
`.env.example` to `.env`. Then follow the printed instructions.

## 4. Configure

```bash
nano .env
```

- `MODE=paper` to start (safe, simulated, no keys needed).
- For **live** later: set `CRYPTOCOM_API_KEY` / `CRYPTOCOM_API_SECRET` (trade
  permission, **withdraw disabled**, IP-restricted to this VM's IP) and `MODE=live`.
- For **AI confirmation**: set `ANTHROPIC_API_KEY` and `ai.enabled: true` in
  `config.yaml`.

## 5. Run it 24/7 (systemd)

```bash
sudo cp deploy/cryptoking.service /etc/systemd/system/
sudo cp deploy/cryptoking-learn.service /etc/systemd/system/
sudo cp deploy/cryptoking-learn.timer  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cryptoking.service        # the bot + dashboard
sudo systemctl enable --now cryptoking-learn.timer    # weekly self-learning
```

The bot now runs continuously and survives reboots. Check it:

```bash
systemctl status cryptoking
journalctl -u cryptoking -f          # live logs
```

> If your VM's username isn't `ubuntu`, edit `User=` and the paths in the two
> `.service` files (and `deploy/setup.sh` printed the same note).

## 6. Open the dashboard (securely)

The dashboard binds to `127.0.0.1` on the VM. Tunnel it to your laptop:

```bash
ssh -L 8000:localhost:8000 ubuntu@<VM_PUBLIC_IP>
```

Then open <http://localhost:8000> in your browser. Use the **Start** button to
begin trading (or set `--autostart` in the service). Nothing is exposed publicly.

> If you ever must expose it directly, put it behind an authenticated reverse
> proxy (Caddy/nginx + basic auth or OAuth) and HTTPS — never raw, especially live.

## 7. Self-learning on a schedule

The `cryptoking-learn.timer` runs `deploy/retune.sh` weekly: it fetches recent
candles and proposes a walk-forward re-tune. By default it only **proposes** —
review and **Approve** it from the dashboard's *Self-learning* panel (stop the
bot first; it's applied on next start). For autonomous adaptation, add `--apply`
in `deploy/retune.sh`.

Check the timer:

```bash
systemctl list-timers cryptoking-learn
journalctl -u cryptoking-learn -f
```

## Updating

```bash
cd ~/cryptoking
git pull
.venv/bin/pip install -r requirements.txt
sudo systemctl restart cryptoking
```

## Cost & footprint

- Oracle **Always Free** VM: $0 forever (within free shapes/limits).
- crypto.com fees still apply to live trades (use maker/limit orders — see README).
- Anthropic credits are used **only if** `ai.enabled: true`, and only on BUY
  signals — a few cents to dollars per month at typical signal rates, depending
  on model (Haiku cheapest).

## Troubleshooting

| Symptom | Check |
|---|---|
| `systemctl status` shows failed | `journalctl -u cryptoking -e` for the traceback |
| Dashboard won't load | SSH tunnel running? Service active? `curl localhost:8000` on the VM |
| Live mode errors on keys | `.env` has both key + secret; key has trade permission; IP allowlist matches the VM |
| Can't reach crypto.com | Oracle egress is open by default; verify with `curl https://api.crypto.com/exchange/v1/public/get-tickers?instrument_name=BTC_USDT` |
