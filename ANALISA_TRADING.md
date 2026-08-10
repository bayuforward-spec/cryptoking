# 📊 Analisa Cara Trading (dari 90 screenshot chart)

Dokumen ini membedah metode trading yang terlihat pada kumpulan screenshot TradingView
yang dikirim (sumber: **kevinjon27 / "KJO ACADEMY - kjoacademy.com"**), lalu memetakannya
ke kode aplikasi **CryptoKing** di repo ini. Tujuannya: memastikan aplikasi benar-benar
mengikuti cara trading pada gambar.

> ⚠️ Ini analisa teknikal untuk keperluan software, **bukan nasihat keuangan**. Trading
> kripto (apalagi perpetual/leverage) berisiko tinggi. Uji di mode `paper` dulu.

---

## 1. Apa yang ada di gambar

Aset yang dianalisa: **BTC, ETH, SOL, SUI, AAVE, HYPE, ETHBTC** — semuanya *perpetual
contract* (Binance / BingX), di berbagai timeframe: **1M (bulanan), 1W, 1D, 4H, 1H**.

Setiap chart memakai pola alat yang **konsisten** dan berulang:

| Elemen di chart | Wujud visual | Fungsi |
|---|---|---|
| **Struktur pasar (multi-timeframe)** | TF besar (1M/1W) untuk arah, TF kecil (4H/1H) untuk entry | Menentukan bias: uptrend / downtrend / range |
| **Support & Resistance** | Garis horizontal putih berlabel harga (mis. `71.273`, `67.242`) | Area pantul + **target TP bertingkat** |
| **Fibonacci retracement** | Label `0.618`, "golden pocket" | Zona **entry** saat harga pullback |
| **Fibonacci extension** | Label TP `1.618`, `2.618`, `2.368` | **Target take-profit** di atas impulse |
| **Trendline** | Garis diagonal kuning | Deteksi breakout / breakdown |
| **Pola chart** | *Falling Wedge*, *Double Bottom*, *Inverse H&S* (busur kuning) | Sinyal reversal |
| **Long/Short Position tool** | Kotak hijau (profit) + kotak merah (risk) | Entry, TP, SL, dan **Risk:Reward** tampil (mis. `2.55`, `2.48`, `6.95`) |
| Indikator tambahan | "Auto Trading Strategy", "Moon Phases", "AG FX Watermark" | Bumbu; inti keputusan tetap price action |

> Catatan: satu screenshot bukan chart — melainkan tangkapan layar admin WhatsApp
> Business soal *refund* pelanggan ("Hendra – Mebel Anugerah"). Itu **tidak berkaitan**
> dengan metode trading dan diabaikan dalam analisa.

---

## 2. Anatomi satu setup (yang diulang di ~semua gambar)

Ambil contoh chart **AAVE 1D** dan **HYPE 4H** yang paling gamblang:

1. **Tentukan arah dari struktur** — harga bikin *higher-high / higher-low* → uptrend,
   jadi hanya cari posisi **LONG**.
2. **Tunggu pullback ke support** — harga turun ke **golden pocket Fibonacci (0.618–0.786)**
   dari impulse naik terakhir, sering berimpit dengan garis support horizontal.
3. **Konfirmasi** — muncul candle reversal bullish / pola (wedge, double bottom) di zona itu.
4. **Pasang order** dengan Long Position tool:
   - **Entry**: harga sekarang di zona support.
   - **Stop-loss (kotak merah)**: sedikit di bawah swing low / support — invalidasi struktur.
   - **Take-profit (kotak hijau)**: di **resistance berikutnya** atau **Fibonacci extension**
     (`1.618`, `2.618`). Di gambar TP dipasang **bertingkat** (beberapa garis).
5. **Kelola risiko** — kotak merah menunjukkan risiko **~1–5%**, kotak hijau reward
   jauh lebih besar (mis. `26.5%`, `36.7%`). Angka **R:R 2.5–6.9** tertera → target minimal
   1:2, sering lebih.

**Intinya:** *trade searah struktur → masuk di support (golden pocket) → SL di bawah
struktur → TP di resistance / fib-extension → jaga R:R ≥ 1:2.*

---

## 3. Pemetaan ke aplikasi (`src/cryptoking/`)

Kabar baik: inti metode ini **sudah** terimplementasi di strategi default `structure_fib`.
Berikut peta persisnya:

| Langkah di gambar | Modul di kode |
|---|---|
| Struktur multi-TF (arah) | `structure.py → market_structure()`; `engine` pakai `trend_timeframe` (TF besar) vs `timeframe` (TF entry) |
| Golden pocket 0.618–0.786 (entry) | `structure.py → fib_retracement()`, `Fib.in_golden_pocket()` |
| Konfirmasi candle | `patterns.py → bullish_reversal()` (hammer, engulfing, tweezer, marubozu) |
| SL di bawah swing low | `strategy/structure_fib.py` → `stop_price = low * (1 - stop_buffer)` |
| Sizing 1% risk + R:R | `risk/risk_manager.py → size_entry()`, `target_for()` |
| Kill-switch harian | `risk/risk_manager.py` (`max_daily_loss_pct`) |

### Yang ditambahkan agar 100% cocok dengan gambar

Gambar memakai **Fibonacci extension** dan **garis Support/Resistance** sebagai target TP —
dua hal yang belum eksplisit di kode. Ditambahkan di update ini:

- `structure.py → fib_extension(low, high)` — proyeksi target `1.272 / 1.618 / 2.0 / 2.618`
  di atas impulse (persis label TP `1.618`/`2.618` di chart AAVE & HYPE).
- `structure.py → support_resistance()` + `levels_relative_to()` — meng-*cluster* swing point
  jadi garis horizontal, lalu menandai mana **resistance** (kandidat TP) di atas harga.
- Strategi `structure_fib` kini:
  - selalu melampirkan `fib_targets` dan `resistances` ke setiap sinyal BUY (tampil di log/dashboard),
  - punya opsi `target_mode` di `config.yaml`:
    - `rr` — TP = kelipatan reward:risk datar (perilaku lama, default),
    - `fib_ext` — TP = Fibonacci extension terdekat di atas entry,
    - `resistance` — TP = resistance horizontal terdekat di atas entry,
  - `min_rr` menjaga target yang dipilih tetap ≥ R:R minimal (buang target terlalu dekat).

Contoh `config.yaml`:

```yaml
strategy:
  name: structure_fib
  params:
    target_mode: fib_ext   # TP mengikuti fib extension, seperti di chart
    min_rr: 1.5            # abaikan target < 1:1.5
```

---

## 4. Perbedaan penting: spot long-only vs perpetual

Gambar memakai **perpetual contract** (bisa LONG & SHORT, pakai leverage). Aplikasi ini
sengaja **long-only di spot** (lebih aman, tanpa risiko likuidasi leverage) — lihat
*Roadmap* di `README.md` untuk rencana klien futures (mis. Bybit) di balik interface
`Broker` yang sudah ada. Jadi metode entry/TP/SL identik, tetapi arah **short belum**
dieksekusi otomatis; setup short di chart bisa dijalankan manual atau menunggu modul futures.

---

## 5. Cara menjalankan (ringkas)

```bash
pip install -r requirements.txt
cp .env.example .env      # MODE=paper (aman, tanpa API key)
python webapp.py          # buka http://localhost:8000
```

Panduan lengkap dari nol: **[PANDUAN.md](PANDUAN.md)**. Uji edge dulu:
`python backtest.py --demo`. Baru `MODE=live` setelah *expected value* positif di 30+ trade.

---

## 6. Ringkasan aturan (checklist metode)

- [ ] Arah dari TF besar: hanya LONG saat uptrend, hanya SHORT saat downtrend.
- [ ] Entry hanya di **support** (golden pocket 0.618–0.786) / pola reversal.
- [ ] Ada konfirmasi candle/pola sebelum masuk.
- [ ] SL selalu di luar struktur (di bawah swing low untuk long).
- [ ] TP di resistance / fib-extension berikutnya, **R:R ≥ 1:2**.
- [ ] Risiko per trade **≤ 1–2%** modal; berhenti kalau kena batas rugi harian.
