/**
 * Google Apps Script — Trigger webhook saat spreadsheet diedit.
 * 
 * CARA INSTALL:
 * 1. Buka Google Sheets yang ingin di-sync
 * 2. Klik menu: Extensions → Apps Script
 * 3. Hapus semua kode yang ada
 * 4. Copy-paste seluruh kode ini
 * 5. Ganti WEBHOOK_URL dengan URL server Anda
 * 6. Ganti WEBHOOK_SECRET dengan secret yang sama di .env
 * 7. Klik "Save" (Ctrl+S)
 * 8. Setup trigger:
 *    a. Klik icon jam (Triggers) di sidebar kiri
 *    b. Klik "+ Add Trigger"
 *    c. Function: onEditTrigger
 *    d. Event type: On edit
 *    e. Klik "Save"
 *    f. Izinkan akses yang diminta
 */

// ═══════════════════════════════════════════════
// KONFIGURASI — Ganti sesuai setup Anda
// ═══════════════════════════════════════════════

// URL webhook server Anda (gunakan ngrok URL jika lokal)
const WEBHOOK_URL = "http://YOUR_SERVER_URL/webhook";

// Secret key yang sama seperti di file .env  
const WEBHOOK_SECRET = "your_webhook_secret_here";

// Debounce: minimal jeda antar trigger (dalam milidetik)
// Mencegah terlalu banyak request saat user edit cepat
const DEBOUNCE_MS = 5000; // 5 detik


// ═══════════════════════════════════════════════
// JANGAN EDIT DI BAWAH INI
// ═══════════════════════════════════════════════

/**
 * Trigger function — dipanggil saat spreadsheet diedit.
 * Mengirim POST request ke webhook server.
 */
function onEditTrigger(e) {
  try {
    // Cek debounce
    const cache = CacheService.getScriptCache();
    const lastTrigger = cache.get("lastTriggerTime");
    const now = new Date().getTime();
    
    if (lastTrigger && (now - parseInt(lastTrigger)) < DEBOUNCE_MS) {
      console.log("Debounce: trigger terlalu cepat, diabaikan.");
      return;
    }
    
    // Set debounce timestamp
    cache.put("lastTriggerTime", now.toString(), 60); // expire after 60s
    
    // Ambil info edit
    const sheet = e.source.getActiveSheet();
    const range = e.range;
    
    const payload = {
      "event": "edit",
      "sheet": sheet.getName(),
      "row": range.getRow(),
      "column": range.getColumn(),
      "value": range.getValue().toString(),
      "secret": WEBHOOK_SECRET,
      "timestamp": new Date().toISOString(),
    };
    
    console.log("Mengirim webhook:", JSON.stringify(payload));
    
    // Kirim POST request ke webhook server
    const options = {
      "method": "post",
      "contentType": "application/json",
      "payload": JSON.stringify(payload),
      "muteHttpExceptions": true,
      "followRedirects": true,
    };
    
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();
    const responseBody = response.getContentText();
    
    console.log(`Webhook response [${responseCode}]: ${responseBody}`);
    
    if (responseCode !== 200) {
      console.error(`Webhook error: ${responseCode} - ${responseBody}`);
    }
    
  } catch (error) {
    console.error("Error di onEditTrigger:", error.toString());
  }
}


/**
 * Test function — jalankan manual untuk test webhook.
 * Klik "Run" di Apps Script editor untuk test.
 */
function testWebhook() {
  const payload = {
    "event": "test",
    "sheet": "Test",
    "row": 1,
    "secret": WEBHOOK_SECRET,
    "timestamp": new Date().toISOString(),
  };
  
  const options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true,
  };
  
  try {
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const responseCode = response.getResponseCode();
    const responseBody = response.getContentText();
    
    console.log(`Test response [${responseCode}]: ${responseBody}`);
    
    if (responseCode === 200) {
      SpreadsheetApp.getUi().alert("✅ Webhook berhasil! Response: " + responseBody);
    } else {
      SpreadsheetApp.getUi().alert("❌ Webhook gagal! Status: " + responseCode + "\n" + responseBody);
    }
  } catch (error) {
    SpreadsheetApp.getUi().alert("❌ Error: " + error.toString());
  }
}
