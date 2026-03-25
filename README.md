# 🤖 Sheets → Trello Sync Bot

Bot Python yang secara otomatis membuat card Trello dari baris-baris di Google Sheets.

## ✨ Fitur

- 📤 **Sync otomatis** — Setiap baris di spreadsheet = 1 card di Trello
- 🔔 **Webhook trigger** — Otomatis sync saat spreadsheet diedit
- 🖱️ **Manual sync** — Jalankan sync kapan saja via CLI atau browser
- 🏷️ **Labels & Due Date** — Support label dan due date dari spreadsheet
- 📝 **Status tracking** — Kolom Status otomatis diupdate setelah sync
- 🔍 **Dry run mode** — Test tanpa membuat card

## 📋 Format Spreadsheet

| A (Nama) | B (Deskripsi) | C (Link) | D (List) | E (Label) | F (Due Date) | G (Status) | H (Card URL) |
|----------|---------------|----------|----------|-----------|---------------|------------|--------------|
| Task 1   | Detail task   | https://... | KPI MARET 2025 | Bug | 2026-04-01 | *(auto)* | *(auto)* |
| Task 2   | Deskripsi     | https://... | KPI APRIL 2025 | Feature | | | |

- **Kolom A**: Nama card (wajib)
- **Kolom B**: Deskripsi card
- **Kolom C**: Link hasil editan (otomatis masuk ke deskripsi card)
- **Kolom D**: Nama list Trello (otomatis dibuat jika belum ada)
- **Kolom E**: Label (pisahkan dengan koma untuk multiple)
- **Kolom F**: Due date (format: YYYY-MM-DD)
- **Kolom G**: Status (diisi otomatis "Synced")
- **Kolom H**: URL card Trello (diisi otomatis)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Credentials

Ikuti panduan lengkap di [setup_guide.md](setup_guide.md):
1. Buat Google Cloud service account & download `credentials.json`
2. Dapatkan Trello API key & token
3. Copy `.env.example` → `.env` dan isi semua nilai

### 3. Cek Koneksi

```bash
# Cek koneksi ke spreadsheet
python manual_sync.py --check-sheet

# Lihat daftar board Trello
python manual_sync.py --list-boards

# Lihat daftar list di board
python manual_sync.py --list-lists
```

### 4. Test Sync

```bash
# Dry run (test tanpa buat card)
python manual_sync.py --dry-run

# Sync manual
python manual_sync.py
```

### 5. Jalankan Webhook Server

```bash
# Terminal 1: Jalankan server
python webhook_server.py

# Terminal 2: Expose via ngrok (opsional, untuk webhook)
ngrok http 5000
```

### 6. Setup Apps Script Trigger

Ikuti langkah di [setup_guide.md](setup_guide.md#3️⃣-setup-google-apps-script-webhook-trigger).

## 📁 Struktur Project

```
sheets-to-trello/
├── config.py              # Konfigurasi dari .env
├── google_sheets.py       # Google Sheets API client
├── trello_client.py       # Trello REST API client
├── sync.py                # Logika sinkronisasi
├── webhook_server.py      # Flask webhook server
├── manual_sync.py         # CLI tool untuk sync manual
├── apps_script.js         # Google Apps Script (copy ke GSheets)
├── requirements.txt       # Python dependencies
├── .env.example           # Template environment variables
├── .env                   # Environment variables (buat sendiri)
├── credentials.json       # Google credentials (download sendiri)
├── setup_guide.md         # Panduan setup lengkap
└── README.md              # Dokumentasi ini
```

## 🔌 API Endpoints (Webhook Server)

| Method | Endpoint    | Deskripsi                          |
|--------|-------------|------------------------------------|
| GET    | `/`         | Info server                        |
| POST   | `/webhook`  | Trigger sync dari Apps Script      |
| GET    | `/sync`     | Trigger sync manual via browser    |
| GET    | `/dry-run`  | Test sync tanpa buat card          |
| GET    | `/health`   | Health check                       |
| GET    | `/history`  | Lihat sync history                 |

## ❓ Troubleshooting

### "Environment variable 'X' belum diset!"
→ Pastikan file `.env` sudah dibuat dan terisi. Copy dari `.env.example`.

### "File credentials tidak ditemukan"
→ Download `credentials.json` dari Google Cloud Console. Lihat [setup_guide.md](setup_guide.md).

### Card tidak muncul di Trello
→ Pastikan `TRELLO_LIST_ID` benar. Jalankan `python manual_sync.py --list-lists` untuk melihat ID list.

### Webhook tidak bekerja
→ Pastikan server berjalan dan URL di Apps Script benar. Test dengan function `testWebhook` di Apps Script.
