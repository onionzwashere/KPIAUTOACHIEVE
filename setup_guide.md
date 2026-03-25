# 📖 Panduan Setup — Sheets → Trello Sync Bot

Panduan langkah-langkah untuk mendapatkan API credentials yang dibutuhkan.

---

## 1️⃣ Google Sheets API (Service Account)

### Langkah-langkah:

1. **Buka Google Cloud Console**
   - Pergi ke [console.cloud.google.com](https://console.cloud.google.com)
   - Login dengan akun Google Anda

2. **Buat Project Baru** (atau pilih project yang sudah ada)
   - Klik dropdown project di atas → "New Project"
   - Beri nama (misalnya: "Sheets Trello Bot")
   - Klik "Create"

3. **Aktifkan Google Sheets API**
   - Pergi ke [APIs & Services → Library](https://console.cloud.google.com/apis/library)
   - Cari "Google Sheets API"
   - Klik "Enable"

4. **Aktifkan Google Drive API**
   - Cari "Google Drive API" di Library
   - Klik "Enable"

5. **Buat Service Account**
   - Pergi ke [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
   - Klik "+ CREATE CREDENTIALS" → "Service account"
   - Nama: "sheets-trello-bot"
   - Klik "Create and Continue"
   - Role: skip (klik "Continue")
   - Klik "Done"

6. **Download Credentials JSON**
   - Di halaman Credentials, klik service account yang baru dibuat
   - Tab "Keys" → "Add Key" → "Create new key"
   - Type: JSON → "Create"
   - File JSON akan terdownload — **simpan sebagai `credentials.json`** di folder project ini

7. **Share Spreadsheet ke Service Account**
   - Buka file `credentials.json`, cari field `"client_email"` — copy email tersebut
   - Buka Google Sheets yang ingin di-sync
   - Klik "Share" → paste email service account → beri akses "Editor"
   - Klik "Send"

8. **Copy Spreadsheet ID**
   - Dari URL spreadsheet: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
   - Copy bagian `{SPREADSHEET_ID}`
   - Paste ke file `.env` → `SPREADSHEET_ID`

---

## 2️⃣ Trello API Key & Token

### Langkah-langkah:

1. **Dapatkan API Key**
   - Buka [trello.com/power-ups/admin](https://trello.com/power-ups/admin)
   - Login dengan akun Trello Anda
   - Klik "New" untuk buat power-up baru (atau gunakan yang ada)
   - Setelah dibuat, klik power-up → tab "API Key"
   - Copy **API Key** → paste ke `.env` → `TRELLO_API_KEY`

2. **Dapatkan Token**
   - Di halaman yang sama, klik link untuk generate token
   - Atau buka URL ini (ganti `{YOUR_API_KEY}` dengan API key Anda):
     ```
     https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key={YOUR_API_KEY}
     ```
   - Klik "Allow"
   - Copy **Token** yang ditampilkan → paste ke `.env` → `TRELLO_TOKEN`

3. **Dapatkan Board ID**
   - Jalankan:
     ```bash
     python manual_sync.py --list-boards
     ```
   - Copy ID board yang diinginkan → paste ke `.env` → `TRELLO_BOARD_ID`

4. **Dapatkan List ID**
   - Jalankan:
     ```bash
     python manual_sync.py --list-lists
     ```
   - Copy ID list yang diinginkan → paste ke `.env` → `TRELLO_LIST_ID`

---

## 3️⃣ Setup Google Apps Script (Webhook Trigger)

### Langkah-langkah:

1. **Buka Google Sheets** yang ingin di-sync

2. **Buka Apps Script Editor**
   - Menu: Extensions → Apps Script

3. **Copy-paste kode**
   - Hapus semua kode yang ada di editor
   - Buka file `apps_script.js` dari project ini
   - Copy seluruh isinya dan paste di editor Apps Script

4. **Konfigurasi**
   - Ganti `WEBHOOK_URL` dengan URL server Anda
     - Untuk lokal: gunakan ngrok URL (lihat langkah 4️⃣)
   - Ganti `WEBHOOK_SECRET` dengan secret yang sama di file `.env`

5. **Save** (Ctrl+S)

6. **Setup Trigger**
   - Klik icon ⏰ (Triggers) di sidebar kiri
   - Klik "+ Add Trigger"
   - Settings:
     - Function: `onEditTrigger`
     - Event source: From spreadsheet
     - Event type: On edit
   - Klik "Save"
   - Izinkan semua akses yang diminta

7. **Test**
   - Di editor, pilih function `testWebhook`
   - Klik "Run"
   - Pastikan muncul alert "✅ Webhook berhasil!"

---

## 4️⃣ Setup Ngrok (untuk Development Lokal)

Ngrok digunakan untuk membuat server lokal bisa diakses dari internet.

### Langkah-langkah:

1. **Install ngrok**
   - Download dari [ngrok.com/download](https://ngrok.com/download)
   - Atau install via:
     ```bash
     # Windows (Chocolatey)
     choco install ngrok
     
     # Atau download manual dan extract
     ```

2. **Daftar akun ngrok** (gratis)
   - Buka [dashboard.ngrok.com](https://dashboard.ngrok.com)
   - Copy auth token

3. **Setup auth token**
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

4. **Jalankan ngrok**
   ```bash
   ngrok http 5000
   ```
   - Copy URL yang ditampilkan (misalnya: `https://abc123.ngrok-free.app`)
   - Paste URL ini ke Apps Script → `WEBHOOK_URL` (tambahkan `/webhook`)
   - Contoh: `https://abc123.ngrok-free.app/webhook`

> ⚠️ **Catatan**: URL ngrok gratis berubah setiap kali restart. Anda perlu update URL di Apps Script setiap kali restart ngrok.

---

## ✅ Checklist Sebelum Menjalankan Bot

- [ ] `credentials.json` ada di folder project
- [ ] Spreadsheet di-share ke service account email
- [ ] File `.env` sudah terisi semua:
  - [ ] `SPREADSHEET_ID`
  - [ ] `TRELLO_API_KEY`
  - [ ] `TRELLO_TOKEN`
  - [ ] `TRELLO_BOARD_ID`
  - [ ] `TRELLO_LIST_ID`
- [ ] Spreadsheet punya format kolom yang benar:
  - Kolom A: Nama
  - Kolom B: Deskripsi
  - Kolom C: Label
  - Kolom D: Due Date
  - Kolom E: Status (kosong, akan diisi otomatis)
- [ ] Apps Script sudah di-setup dengan trigger
- [ ] Webhook URL di Apps Script sudah benar
