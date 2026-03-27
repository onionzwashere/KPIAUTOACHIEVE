// Ini adalah script yang harus Anda masukkan ke Google Sheets (Extensions -> Apps Script).
// Script ini akan memunculkan menu khusus "🤖 Trello Sync" di bagian atas Google Sheets Anda,
// sehingga Anda bisa melakukan sync kapan saja hanya dengan menekan tombol menu tersebut.

const WEBHOOK_URL = "MASUKKAN_URL_NGROK_ANDA_DISINI/webhook"; // Contoh: https://1234-abcd.ngrok.app/webhook

// Fungsi ini berjalan otomatis saat Sheet pertama kali dibuka untuk membuat Menu
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🤖 Trello Sync')
      .addItem('▶️ Sync Sheet Ini Sekarang', 'triggerSync')
      .addToUi();
}

// Fungsi yang dijalankan ketika Anda mengklik tombol "Sync Sheet Ini Sekarang" di menu
function triggerSync() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const sheetName = sheet.getName();
  
  // Tampilkan notifikasi loading (Toast) di pojok kanan bawah layar Sheet
  SpreadsheetApp.getActiveSpreadsheet().toast('Silakan tunggu... Bot Trello sedang memproses.', '⏳ Memulai Sync', 5);
  
  // Siapkan data untuk dikirim ke bot webhook_server.py
  const payload = {
    "event": "manual_trigger_from_menu",
    "sheet": sheetName,
    "secret": "" // Isi jika Anda mengatur WEBHOOK_SECRET di .env bot Anda
  };
  
  const options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true // Menangkap error http tanpa crash script
  };
  
  // Kirim data ke URL Webhook bot
  try {
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    const code = response.getResponseCode();
    
    if (code === 200 || code === 201) {
      SpreadsheetApp.getActiveSpreadsheet().toast('Bot berhasil merespons dan sedang/sudah memproses sinkronisasi sheet ini!', '✅ Selesai', 8);
    } else {
      SpreadsheetApp.getUi().alert('❌ Server merespons dengan error kode: ' + code + '\nPastikan server Python berjalan normal.');
    }
  } catch(err) {
    SpreadsheetApp.getUi().alert('🚨 Gagal menghubungi Webhook Server.\n\nPastikan ngrok sudah berjalan dan URL di dalam script ini sudah diganti ke URL ngrok terbaru.\n\nError: ' + err);
  }
}
