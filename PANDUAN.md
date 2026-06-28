# 📖 Panduan Lengkap CryptoKing (Bahasa Indonesia)

Panduan dari **nol sampai jalan**, ditulis untuk pemula. Ikuti urut dari atas.
Jangan loncat tahap — terutama jangan langsung pakai uang nyata.

> ⚠️ **PERINGATAN PENTING — BACA DULU**
> - Trading kripto **berisiko kehilangan uang nyata**. Bot tidak menjamin profit.
> - Strategi bawaan **belum terbukti profit** — wajib diuji dulu (Tahap 3 & 4).
> - Di Indonesia, trading kripto diatur **Bappebti/OJK**. Exchange luar seperti
>   crypto.com mungkin tidak teregulasi untuk WNI — cek sendiri sebelum pakai uang.
> - **Mulai dari mode paper (simulasi)**. Uang nyata hanya setelah edge terbukti.

---

## Daftar Isi

1. [Gambaran besar: ini sebenarnya apa?](#1-gambaran-besar)
2. [Istilah penting (kamus singkat)](#2-istilah-penting)
3. [Tahap 0 — Yang perlu disiapkan](#3-tahap-0--persiapan)
4. [Tahap 1 — Deploy ke server gratis (Oracle Cloud)](#4-tahap-1--deploy)
5. [Tahap 2 — Paper trading (simulasi)](#5-tahap-2--paper-trading)
6. [Tahap 3 — Backtest & tuning](#6-tahap-3--backtest--tuning)
7. [Tahap 4 — Self-learning](#7-tahap-4--self-learning)
8. [Tahap 5 — AI filter (opsional)](#8-tahap-5--ai-filter-opsional)
9. [Tahap 6 — Live (uang nyata)](#9-tahap-6--live-uang-nyata)
10. [Mengatur strategi & risiko](#10-mengatur-strategi--risiko)
11. [Masalah umum & solusi](#11-masalah-umum--solusi)
12. [Checklist sebelum live](#12-checklist-sebelum-live)

---

## 1. Gambaran besar

CryptoKing adalah **bot trading otomatis** untuk BTC/ETH di crypto.com. Alurnya:

```
[Harga crypto.com] → [Strategi: structure + Fibonacci + candlestick]
   → [Filter AI opsional (Claude)] → [Manajemen risiko 1%] → [Eksekusi order]
   → [Dashboard web + jurnal]
```

Botnya jalan sebagai program yang **nyala terus 24/7** di sebuah server. Kamu
pantau & kontrol lewat **dashboard web**. Ada **3 mode kerja**:

| Mode | Uang | Kapan dipakai |
|---|---|---|
| **Paper** | Simulasi (harga asli, tanpa uang) | Wajib mulai di sini |
| **Backtest** | Data historis | Uji strategi sebelum jalan |
| **Live** | Uang nyata | Hanya setelah edge terbukti |

---

## 2. Istilah penting

- **Paper trading** — latihan pakai uang bohongan tapi harga asli. Nol risiko.
- **Backtest** — uji strategi atas data harga masa lalu.
- **Edge / Expected Value (EV)** — rata-rata untung per trade. Harus **positif**
  baru layak live. Inti dari semua: *kamu tak perlu menang tiap kali, asal saat
  menang lebih besar daripada saat kalah.*
- **Risk per trade** — berapa % modal yang dipertaruhkan tiap trade. Bot ini 1%.
- **R:R (reward:risk)** — rasio target untung vs stop rugi. Default 2:1.
- **Stop-loss** — harga batas rugi, posisi ditutup otomatis. **Take-profit** — batas untung.
- **Maker/taker** — limit order (maker, fee murah) vs market order (taker, fee mahal).
- **Walk-forward** — cara "belajar" yang menguji parameter di data yang belum dilihat,
  supaya tidak menipu diri (overfit).
- **VPS/VM** — komputer di cloud yang nyala 24/7.

---

## 3. Tahap 0 — Persiapan

Yang kamu butuhkan (semua bisa disiapkan gratis dulu):

1. **Komputer/laptop** dengan terminal (Mac/Linux bawaan; Windows pakai PowerShell
   atau WSL).
2. **Akun GitHub** (kode ada di sini) — sudah ada.
3. **Akun Oracle Cloud** (gratis) — untuk server 24/7. Daftar di
   <https://www.oracle.com/cloud/free/>. Butuh kartu (untuk verifikasi, **tidak
   ditagih** selama pakai shape Always Free).
4. *(Nanti, opsional)* **API key crypto.com** — hanya untuk mode live.
5. *(Nanti, opsional)* **API key Anthropic** — hanya kalau mau filter AI.

> Belum perlu deposit uang apa pun di Tahap 0–4.

---

## 4. Tahap 1 — Deploy

Tujuan: bot nyala 24/7 di server gratis, mode paper. Panduan teknis lengkap ada
di **[DEPLOY.md](DEPLOY.md)** — ringkasnya:

### 4.1 Buat VM gratis di Oracle Cloud

1. Login Oracle Cloud → **Compute → Instances → Create Instance**.
2. **Image**: Ubuntu 22.04. **Shape**: yang berlabel *Always Free* (mis.
   `VM.Standard.A1.Flex` atau `E2.1.Micro`).
3. Tambahkan **SSH key** (atau unduh keypair dari Oracle).
4. Catat **Public IP** instance-nya.
5. Inbound port: cukup **SSH (22)**. Dashboard diakses lewat tunnel, jadi aman.

### 4.2 Masuk ke server & ambil kode

Dari terminal laptopmu:

```bash
ssh ubuntu@<PUBLIC_IP>
git clone https://github.com/bayuforward-spec/cryptoking.git
cd cryptoking
git checkout claude/crypto-trading-bot-cy5qq2
```

### 4.3 Pasang otomatis

```bash
bash deploy/setup.sh
```

Script ini memasang Python, bikin virtualenv, install dependensi, dan menyalin
`.env.example` → `.env`. Ikuti instruksi yang dicetak di akhir.

### 4.4 Konfigurasi

```bash
nano .env
```
Pastikan `MODE=paper` (default). **Jangan isi API key dulu.** Simpan (Ctrl-O,
Enter, Ctrl-X).

### 4.5 Nyalakan 24/7 (systemd)

```bash
sudo cp deploy/cryptoking.service /etc/systemd/system/
sudo cp deploy/cryptoking-learn.service /etc/systemd/system/
sudo cp deploy/cryptoking-learn.timer  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cryptoking.service
sudo systemctl enable --now cryptoking-learn.timer
```

Cek jalan: `systemctl status cryptoking` (harus `active (running)`).
Lihat log langsung: `journalctl -u cryptoking -f` (Ctrl-C untuk keluar).

### 4.6 Buka dashboard (aman)

Dari laptopmu (terminal baru):

```bash
ssh -L 8000:localhost:8000 ubuntu@<PUBLIC_IP>
```
Biarkan terminal ini terbuka, lalu buka browser ke **http://localhost:8000**.

> Dashboard hanya bisa diakses lewat tunnel ini — tidak terekspos ke internet.

---

## 5. Tahap 2 — Paper trading

Sekarang botnya hidup tapi belum trading. Di dashboard:

1. Pastikan badge mode tertulis **PAPER** (hijau).
2. Klik **▶ Start**. Status berubah jadi *running*, titik hijau menyala.
3. Amati:
   - **Market & Signals** — harga + sinyal tiap koin (BUY/SELL/HOLD + alasan + RSI).
   - **Open Positions** — posisi terbuka, dengan Stop & Target.
   - **Your Edge** — win rate, **Expected Value per trade**, profit factor (terisi
     setelah ada trade tertutup).
   - **Recent Trades** — riwayat.

**Biarkan jalan beberapa hari.** Strategi `structure_fib` sangat selektif (butuh
uptrend + golden pocket + candle bullish), jadi wajar kalau trade jarang. Itu
desain — kualitas di atas kuantitas.

> Yang kamu tunggu: setelah ~20–30 trade tertutup, lihat **Expected Value**.
> Hijau & positif = ada potensi edge. Merah = strategi belum cocok, lanjut tuning.

Stop kapan saja dengan tombol **■ Stop**.

---

## 6. Tahap 3 — Backtest & tuning

Daripada menunggu berhari-hari, uji strategi atas data historis dulu.

### 6.1 Ambil data harga asli

Di server (lewat SSH):

```bash
cd ~/cryptoking
.venv/bin/python backtest.py --fetch data/BTC_USDT.csv --instrument BTC_USDT
```

### 6.2 Jalankan backtest

```bash
.venv/bin/python backtest.py --csv data/BTC_USDT.csv --instrument BTC_USDT
```

Outputnya menampilkan: jumlah trade, win rate, R:R, profit factor, dan
**expected value per trade**. Kalau ada tulisan *POSITIVE EDGE ✅* → bagus.
Kalau *no edge ❌* → lanjut tuning.

### 6.3 Cari parameter terbaik (tuner)

```bash
.venv/bin/python optimize.py --csv data/BTC_USDT.csv
```

Ini mencoba banyak kombinasi parameter dan **mengurutkan berdasarkan EV**. Lihat
baris teratas — itu kandidat config terbaik. Catatan jujur: kalau semua negatif,
jangan dipaksakan. Lebih baik tidak trade daripada trade rugi.

> 💡 Data dari `--fetch` jumlahnya terbatas (candle terbaru saja). Untuk backtest
> serius, makin banyak data makin valid (lihat roadmap: pagination).

---

## 7. Tahap 4 — Self-learning

Bot bisa **mengusulkan** perbaikan parameter sendiri, dengan aman (anti-overfit).

### 7.1 Jalankan manual

```bash
.venv/bin/python learn.py --csv data/BTC_USDT.csv
```

Prosesnya: data dibagi **train** (lama) + **holdout** (baru) → cari parameter
terbaik di train → uji di holdout (data yang belum dilihat) → **usulkan promosi
HANYA kalau menang di holdout**. Hasil ditulis ke `logs/proposal.json`.

### 7.2 Approve dari dashboard

Buka panel **"Self-learning"** di dashboard. Kalau ada usulan **PROMOTE**, kamu
lihat perbandingan EV current vs proposed di data holdout. Untuk menerapkannya:
1. Klik **■ Stop** (bot harus berhenti dulu).
2. Klik **✅ Approve & apply** di panel Self-learning.
3. Klik **▶ Start** lagi — config baru aktif.

### 7.3 Otomatis mingguan

Timer systemd (`cryptoking-learn.timer`) sudah menjalankan ini tiap minggu dan
menulis usulan. Default: **hanya mengusulkan** (kamu approve manual). Kalau mau
otonom penuh, edit `deploy/retune.sh` dan tambahkan `--apply`.

> Bot **tidak pernah** mengubah aturan live diam-diam. Promosi harus lolos uji
> holdout, dan penerapan butuh persetujuanmu (atau flag eksplisit).

---

## 8. Tahap 5 — AI filter (opsional)

Claude bisa jadi "pendapat kedua" sebelum tiap order BUY.

1. Dapatkan **Anthropic API key** dari <https://console.anthropic.com>.
2. Di server: `nano .env` → isi `ANTHROPIC_API_KEY=sk-ant-...`
3. Install: `.venv/bin/pip install anthropic`
4. Di dashboard panel **Settings** → **AI confirmation: on** → pilih model
   (Haiku paling murah) → **Save** (bot harus stop dulu).

Tiap sinyal BUY akan dikirim ke Claude; kalau Claude veto, trade di-skip. Alasan
AI muncul di baris sinyal. Hemat: hanya jalan saat ada sinyal, bukan tiap detik.

> Inilah pemakaian credit Anthropic yang benar — AI jadi bagian otak bot.
> Credit Anthropic **tidak bisa** dipakai untuk hosting bot (itu tugas server).

---

## 9. Tahap 6 — Live (uang nyata)

**Hanya lakukan ini kalau:** backtest + paper menunjukkan **EV positif konsisten**
dan kamu paham risikonya. Mulai dengan modal yang **siap kamu hilangkan**.

### 9.1 Buat API key crypto.com

Di crypto.com Exchange → **Settings → API Keys → Create**:
- ✅ Aktifkan izin **Trade**.
- ❌ **Matikan izin Withdraw** (penting — biar bot tak bisa menarik dana).
- 🔒 Batasi **IP** ke Public IP server Oracle-mu.

### 9.2 Konfigurasi live

Di server `nano .env`:
```
CRYPTOCOM_API_KEY=...
CRYPTOCOM_API_SECRET=...
MODE=live
```

Di `config.yaml`, set modal kecil dulu:
```yaml
risk:
  starting_capital: 50.0   # sesuaikan dengan saldo riil kecilmu
```
Pakai maker order untuk fee murah (`execution.order_type: limit` — sudah default).

### 9.3 Restart & pantau ketat

```bash
sudo systemctl restart cryptoking
journalctl -u cryptoking -f
```
Di dashboard, badge berubah jadi **LIVE** (merah). **Awasi beberapa trade pertama
secara langsung.** Kill switch harian (`max_daily_loss_pct`) otomatis menghentikan
entry baru kalau rugi harian melewati batas.

---

## 10. Mengatur strategi & risiko

Semua bisa diubah dari panel **Settings** di dashboard (tanpa edit file), atau di
`config.yaml`. Yang penting:

| Pengaturan | Arti | Default |
|---|---|---|
| `risk_per_trade` | % modal dipertaruhkan tiap trade | 0.01 (1%) |
| `rr_ratio` | Target untung : risiko | 2.0 |
| `max_open_positions` | Maks posisi terbuka bersamaan | 2 |
| `max_daily_loss_pct` | Kill switch rugi harian | 0.05 (5%) |
| `timeframe` / `trend_timeframe` | TF eksekusi / arah | 15m / 4h |
| `swing_k` | Sensitivitas deteksi struktur | 3 |
| `order_type` | limit (maker) / market (taker) | limit |

> Aturan emas dari guide: **jangan pernah risk > 1–2% per trade.** Buktikan profit
> dulu sebelum naikkan apa pun.

---

## 11. Masalah umum & solусi

| Gejala | Solusi |
|---|---|
| `systemctl status` → failed | `journalctl -u cryptoking -e` untuk lihat error |
| Dashboard tak terbuka | Tunnel SSH masih jalan? Service `active`? Coba `curl localhost:8000` di server |
| Tidak ada trade berhari-hari | Normal — strategi selektif. Cek panel Signals untuk alasan HOLD |
| Live error soal API key | `.env` ada key+secret; izin Trade aktif; IP allowlist cocok dengan IP server |
| Tak bisa konek crypto.com | Tes: `curl https://api.crypto.com/exchange/v1/public/get-tickers?instrument_name=BTC_USDT` |
| EV terus negatif | Strategi belum cocok untuk kondisi pasar ini — jangan dipaksa live |
| Self-learning selalu "rejected" | Bagus — artinya tak ada config yang lolos uji holdout. Jangan paksa promosi |

---

## 12. Checklist sebelum live

Jangan live sebelum semua ini ✅:

- [ ] Sudah backtest di data crypto.com asli, **EV positif**.
- [ ] Sudah paper trading minimal beberapa hari, hasil konsisten dengan backtest.
- [ ] Paham bahwa bot bisa rugi & kamu siap kehilangan modal yang dipakai.
- [ ] API key crypto.com: izin Trade ON, **Withdraw OFF**, IP dibatasi.
- [ ] `MODE=live` + `starting_capital` kecil.
- [ ] `order_type: limit` (fee murah).
- [ ] Kill switch harian aktif (`max_daily_loss_pct`).
- [ ] Sudah cek aspek legal/pajak di Indonesia (Bappebti/OJK).
- [ ] Siap mengawasi beberapa trade pertama secara langsung.

---

## Ringkasan alur

```
Tahap 0  Siapkan akun (Oracle Cloud gratis)
Tahap 1  Deploy 24/7 (DEPLOY.md)            → bot hidup, mode paper
Tahap 2  Paper trading                       → amati Your Edge
Tahap 3  Backtest + tuning                   → cari config EV positif
Tahap 4  Self-learning                       → adaptasi aman, approve manual
Tahap 5  AI filter (opsional)                → Claude sebagai pendapat kedua
Tahap 6  Live — HANYA jika edge terbukti     → modal kecil, awasi ketat
```

Selamat mencoba, dan **utamakan keamanan modal di atas keserakahan.** 👑
