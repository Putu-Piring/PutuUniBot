# Putu Piring Uni 🍮

Selamat datang ke repositori rasmi **Putu Piring Uni**!

Perniagaan ini merupakan projek keusahawanan sebenar yang diusahakan oleh **mahasiswa Diploma UiTM** bagi memenuhi keperluan kursus wajib **ENT300 (Fundamentals of Entrepreneurship)**.

> **Rujukan Kursus:** [`D:\RepoTools\GitHub\uitm-course\ENT300`](file:///D:/RepoTools/GitHub/uitm-course/ENT300)  
> **Pendaftaran Perniagaan (MASMED MyENT):** [Lihat Sijil Rasmi](docs/certificates/README.md)  
> **Bot Telegram Rasmi:** [@putu_uni_bot](https://t.me/putu_uni_bot)  
> **Model Operasi:** Pra-pesanan Sahaja (Pre-order Only)  
> **Kapasiti Harian:** Terhad (Pra-pesanan awal amat digalakkan)  
> **Sistem Pangkalan Data:** SQLite (`orders.db` melalui `db.py`)  

---

## 📅 Jadual Hari Operasi & Waktu Tutup Pesanan

| Hari | Status | Tutup Pre-order | Waktu Self-Pickup | Waktu Delivery (Runner) |
| :--- | :---: | :---: | :--- | :--- |
| **Ahad** | 🟢 **Buka** | **9:30 AM** (hari sama) | **4:00 PM – 5:00 PM** *(Kawasan Kabin UiTM)* | **4:00 PM – 6:00 PM** *(Caj RM0.50)* |
| **Isnin** | 🟢 **Buka** | **5:00 PM** (hari sama) | **6:30 PM – 9:00 PM** *(Sebelah Warung Cik Malik)* | **6:30 PM – 9:00 PM** *(Caj RM0.50)* |
| **Selasa** | 🟢 **Buka** | **5:00 PM** (hari sama) | **6:30 PM – 9:00 PM** *(Sebelah Warung Cik Malik)* | **6:30 PM – 9:00 PM** *(Caj RM0.50)* |
| **Rabu** | 🔴 **Tutup** | - | *Cuti / Tiada Operasi* | *Cuti / Tiada Operasi* |
| **Khamis** | 🟢 **Buka** | **5:00 PM** (hari sama) | **6:30 PM – 9:00 PM** *(Sebelah Warung Cik Malik)* | **6:30 PM – 9:00 PM** *(Caj RM0.50)* |
| **Jumaat** | 🔴 **Tutup** | - | *Cuti / Tiada Operasi* | *Cuti / Tiada Operasi* |
| **Sabtu** | 🔴 **Tutup** | - | *Cuti / Tiada Operasi* | *Cuti / Tiada Operasi* |

*Nota Penting:*
- **Pembatalan / Pindaan Pesanan:** Hanya dibenarkan **sebelum waktu cut-off** (9:30 AM Ahad / 5:00 PM hari biasa).
- **Notis Stok Habis:** Waktu tutup pesanan harian juga boleh dimaklumkan lebih awal sekiranya stok harian habis.

---

## 🍽️ Produk & Senarai Menu

Putu Piring kami dijual hanya dalam **satu perisa original**:
* **Inti Gula Merah & Kelapa Parut Putih** — Manis beraroma dengan kelapa parut putih segar.
* **Pembungkusan Tradisi** — Dibalut kemas dengan **kertas minyak**.
* **Nota Kesegaran:** Enak dimakan segera semasa panas. Jika disimpan, masukkan ke dalam peti sejuk dan kukus 2 minit (kelapa parut segar cepat basi jika dibiar terdedah).

### 📜 Pilihan Pakej & Status Ketersediaan
| Pakej | Butiran | Kuantiti | Harga | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Pakej 1** | Satu Set Putu Piring Asli | 2 biji | **RM 2.00** | 🟢 **Tersedia (Aktif)** |
| **Pakej 2** | Satu Set Putu Piring + Kopi-O | 2 biji + Kopi-O | **RM 2.50** | 🟡 **Akan Datang (Belum Dibuka)** |

---

## 🛵 Kaedah Penerimaan: Delivery & Self-Pickup

### 1. Penghantaran Runner (Delivery - Caj RM0.50)
- **Zon Liputan:** Kawasan Kampus UiTM, Kawasan RPTU, dan Kawasan Fasa 5 (Lembah Bujang).
- **Titik Serahan:** Pelanggan perlu menunggu di tempat yang ditetapkan runner atau dipersetujui bersama (lobi blok kolej, guard house, kafe kolej).
- **Ahad:** 4:00 PM – 6:00 PM
- **Isnin, Selasa, Khamis:** 6:30 PM – 9:00 PM

### 2. Ambil Sendiri (Self-Pickup - Percuma)
- **Ahad (4:00 PM – 5:00 PM):**
  - **Lokasi:** **Kawasan Kabin UiTM** (Pre-order tutup 9:30 AM).
- **Isnin, Selasa, Khamis (6:30 PM – 9:00 PM):**
  - **Landmark:** Tepat di sebelah **Warung Santai Cik Malik**
  - **Alamat:** 240B Taman Lembah Bujang Utama 8/2, Taman Lembah Bujang, 08100 Bedong, Kedah ([Google Maps](https://maps.app.goo.gl/b9YGPZtXLkSVwF4h8))

---

## 📞 Pegawai Perhubungan / PIC
- **Bot Telegram:** [@putu_uni_bot](https://t.me/putu_uni_bot)
- **Aiman (Runner / PIC):** `011-39163313`
- **Nasrul (Pengurusan / PIC):** `019-4464970`

---

## 🗄️ Pangkalan Data Pesanan SQLite (`orders.db`)
Sistem dilengkapi skrip CLI `db.py` untuk operasi harian dan pelaporan ENT300:
- **Inisialisasi Schema:** `python db.py init`
- **Tambah Pesanan:** `python db.py add --customer "Ali" --phone "0123456789" --qty 2 --type delivery --zone "UiTM" --address "Kolej Dahlia"`
- **Dapatkan Butiran Pesanan:** `python db.py get --ref PPU-20261025-001`
- **Kemas Kini Status Bayaran:** `python db.py update-payment --ref PPU-20261025-001 --status paid --notes "Resit disahkan"`
- **Semak Had Kuota Harian:** `python db.py count`
- **Senarai Pesanan:** `python db.py list --date 2026-10-25`
- **Laporan Jualan & Runner (ENT300):** `python db.py summary --date 2026-10-25`

---

## 💳 Penjana Dynamic DuitNow QR (`qr_generator.py`)
Modul penjanaan kod DuitNow QR Dinamik mengikut standard kebangsaan PayNet Malaysia (EMVCo MPM):
- **Ciri-Ciri Utama:**
  - **Tag 54 (Transaction Amount):** Amaun tepat dijana mengikut jumlah pesanan (cth: RM 2.50, RM 4.50).
  - **Tag 62.01 (Bill Number):** Nombor ID Pesanan (cth: `PPU-20261025-001`).
  - **Tag 63 (CRC16 Checksum):** Pengiraan automatik ISO/IEC 13239 CRC-16/CCITT-FALSE.
  - **Penjanaan Imej Kad Bayaran:** Menghasilkan fail PNG bersaiz mesra telefon pintar lengkap dengan lencana jenama.
  - **Penghantaran Telegram Automatik:** Menyokong penghantaran terus imej ke chat pelanggan menggunakan Telegram Bot API.
- **Arahan CLI:**
  - Ujian Integriti: `python qr_generator.py test`
  - Jana QR Dinamik: `python qr_generator.py generate --amount 4.50 --ref PPU-20261025-001`
  - Periksa Struktur Payload EMVCo: `python qr_generator.py parse --payload "<Payload_String>"`
  - Kemas Kini QR Statik Peniaga: `python qr_generator.py set-static --payload "<Static_Payload>"`

---

## 📁 Struktur Projek

- [`AGENTS.md`](AGENTS.md) — Panduan arahan dan persona keusahawanan siswa untuk ejen AI Telegram.
- [`db.py`](db.py) — Pengurusan pangkalan data SQLite pesanan dan pelaporan ENT300.
- [`qr_generator.py`](qr_generator.py) — Penjana payload EMVCo DuitNow QR dinamik dan kad pembayaran PNG.
- [`config.json`](config.json) — Konfigurasi profil kedai, token bot, dan payload DuitNow asas.
- [`orders.db`](orders.db) — Pangkalan data SQLite pesanan pelanggan.
- [`orders/qr/`](orders/qr/) — Direktori simpanan fail kad imej DuitNow QR yang dijana.
- [`menu.json`](menu.json) — Senarai menu, pakej, jadual operasi, zon penghantaran, lokasi pickup, dan PIC.
- [`payment_info.md`](payment_info.md) — Maklumat pembayaran, spesifikasi DuitNow QR, dan senarai PIC.
- [`docs/BUSINESS_NARRATIVE.md`](docs/BUSINESS_NARRATIVE.md) — Naratif strategik perniagaan, 4 tiang nilai (*value proposition*), segmentasi pasaran, 5 fasa saluran Osterwalder, dan model hubungan pelanggan ENT300.
