# 📋 Trading Plan — CryptoKing (BTC/ETH)

> Dokumen ini adalah **aturan main pribadi** kamu. Bot menjalankan sinyal teknikal;
> dokumen ini mengatur **keputusan & disiplin** kamu sebagai pemilik modal.
> Tempel di dekat meja. Baca ulang tiap sebelum mengubah apa pun.

**Pemilik:** bayuforward · **Dibuat:** 14 Nov 2026 · **Aset:** BTC/USDT, ETH/USDT (spot)
**Platform:** crypto.com (via bot CryptoKing) · **Arah:** LONG-only (beli di uptrend)

---

## 1. Tujuan & filosofi

- **Tujuan utama fase ini:** *membuktikan ada edge (EV positif)* — BUKAN cari cuan cepat.
- **Prinsip inti:** aku tidak perlu menang tiap kali. Aku perlu **saat menang lebih besar
  daripada saat kalah**, dan **mengikuti sistem apa pun hasilnya**.
- **Definisi "menang":** mengikuti aturan. Kalau aku ikut aturan tapi rugi = trade bagus.
  Kalau aku langgar aturan tapi untung = trade jelek (tak bisa diulang).
- **Kerugian = biaya operasional**, bukan kegagalan. Yang dikejar: pendapatan > biaya.

---

## 2. Aturan risiko (TIDAK BISA DITAWAR)

| Aturan | Nilai | Alasan |
|---|---|---|
| Risk per trade | **1%** dari modal | Bisa kalah 10x beruntun, modal masih 90% |
| Reward : Risk minimum | **2 : 1** | Dengan R:R 2:1, cukup menang >33% untuk profit |
| Maks posisi terbuka | **2** | Jangan over-expose |
| Stop-loss | **wajib**, di luar zona support | Tanpa stop = judi |
| Kill switch harian | **-5%** | Kalau rugi 5% sehari, STOP total hari itu |
| Naikkan risk? | **TIDAK**, sampai profit terbukti | Buktikan dulu baru bicara besar |

> Jangan pernah risk > 1–2% per trade. Titik.

---

## 3. Kriteria ENTRY (kapan boleh beli)

Bot otomatis menerapkan ini, tapi aku harus paham & setuju:

1. **Searah struktur** — timeframe besar (4H) harus **uptrend** (higher-high, higher-low).
   Kalau downtrend/ranging → **tidak entry**.
2. **Di support** — harga pullback ke **golden pocket (Fibonacci 0.618–0.786)**.
3. **Konfirmasi candle** — ada pola bullish (hammer / bullish engulfing / tweezer bottom).
4. **Stop jelas** — di bawah swing low. R:R ke target ≥ 2:1.
5. *(Opsional)* **AI filter** — Claude tidak veto setup-nya.

**Kalau salah satu tidak terpenuhi → WAIT. Sabar itu posisi.**

---

## 4. Kriteria EXIT (kapan keluar)

- **Take-profit:** otomatis di **2× jarak stop** (R:R 2:1).
- **Stop-loss:** otomatis di bawah swing low (≈ -1% dari entry pada sizing default).
- **Exit lebih awal:** kalau struktur 4H berubah jadi downtrend, atau muncul candle
  bearish reversal (shooting star / bearish engulfing) — bot akan SELL.
- **Jangan geser stop menjauh** supaya "kasih napas". Itu cara blow-up akun.

---

## 5. Sikap untuk kondisi pasar SEKARANG (bearish)

> Per 14 Nov 2026: BTC & ETH **DOWNTREND kuat** (semua MA = SELL), oversold ekstrem
> (RSI-6 di bawah 10), banyak likuidasi & ETF outflow, BTC terendah sejak Agustus.

**Keputusan:** **TIDAK ADA LIVE TRADING sekarang.**
- Pasar turun + long-only = bot otomatis **HOLD** (benar, lindungi modal).
- Ini **waktu terbaik untuk belajar & paper trading**, bukan taruh uang.
- Tunggu struktur berubah jadi **uptrend** dulu. Jangan "tangkap pisau jatuh".

---

## 6. Rencana bertahap (jangan loncat)

| Fase | Syarat lulus | Target waktu |
|---|---|---|
| **1. Backtest** | EV positif di data crypto.com asli | Minggu 1 |
| **2. Tuning** | Config dengan EV positif lolos uji holdout | Minggu 1–2 |
| **3. Paper trading** | 25–50 trade, hasil konsisten dgn backtest | Minggu 2–4 |
| **4. Self-learning** | Jalan mingguan, approve manual | Berkelanjutan |
| **5. Live (modal kecil)** | HANYA jika Fase 1–3 EV positif **DAN** pasar uptrend | Setelah lulus |

**Modal awal live:** maksimal yang **siap kuhilangkan** (mulai Rp 500rb–1jt). Pakai
**maker/limit order** (fee murah). Naikkan modal **hanya** setelah ≥1 bulan live positif.

---

## 7. Disiplin harian (anti-emosi)

- ❌ **Jangan revenge trade** — habis rugi, jangan balas dendam dengan trade lebih besar.
- ❌ **Jangan ubah aturan di tengah jalan** karena takut/serakah.
- ❌ **Jangan tambah koin/leverage** sebelum profit terbukti.
- ✅ **Jurnal tiap trade** — bot catat otomatis di dashboard (panel "Your Edge").
- ✅ **Review mingguan** — cek win rate, EV, profit factor. EV negatif → stop live, balik tuning.
- ✅ **Satu strategi, diikuti konsisten.** Strategi medioker + disiplin > strategi hebat + emosi.

---

## 8. Checklist sebelum pindah ke LIVE

- [ ] Backtest di data asli → **EV positif**
- [ ] Paper trading 25–50 trade → konsisten
- [ ] Self-learning tidak menolak terus (ada config lolos holdout)
- [ ] **Pasar sedang uptrend** (bukan bearish seperti sekarang)
- [ ] API key crypto.com: Trade ON, **Withdraw OFF**, IP dibatasi
- [ ] Modal kecil, `order_type: limit`, kill switch aktif
- [ ] Siap mengawasi beberapa trade pertama & siap rugi

---

## 9. Angka kunci (ringkasan cepat)

```
Risk/trade ....... 1%
R:R minimum ...... 2:1
Win rate impas ... >33% (pada R:R 2:1)
Maks posisi ...... 2
Kill switch ...... -5%/hari
Order type ....... limit (maker)
Arah ............. LONG-only, hanya di uptrend
Kondisi sekarang . BEARISH → HOLD, paper only
```

---

> **Ini bukan nasihat keuangan.** Trading crypto berisiko kehilangan modal. Patuhi
> regulasi Indonesia (Bappebti/OJK). Rencana ini bisa direvisi — tapi hanya di luar
> jam trading, dengan kepala dingin, dan dicatat alasannya. 👑
