"""
Webhook Server — Flask server yang menerima trigger dari Google Apps Script.
Ketika spreadsheet diedit, Apps Script akan mengirim POST request ke server ini,
yang kemudian menjalankan sinkronisasi.
"""

import hmac
import hashlib
from datetime import datetime

from flask import Flask, request, jsonify

import config
import sync

app = Flask(__name__)

# Track sync history
sync_history = []


@app.route("/", methods=["GET"])
def home():
    """Halaman utama — info server."""
    return jsonify({
        "status": "running",
        "service": "Sheets → Trello Sync Bot",
        "endpoints": {
            "POST /webhook": "Trigger sync dari Google Apps Script",
            "GET /sync": "Trigger sync manual",
            "GET /health": "Health check",
            "GET /history": "Lihat sync history",
        },
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Webhook endpoint — menerima trigger dari Google Apps Script.
    
    Expected POST body (JSON):
    {
        "event": "edit",
        "sheet": "Sheet1",
        "row": 5,
        "secret": "your_webhook_secret"  (opsional)
    }
    """
    data = request.get_json(silent=True) or {}

    # Validasi secret jika dikonfigurasi
    if config.WEBHOOK_SECRET:
        received_secret = data.get("secret", "")
        if not hmac.compare_digest(received_secret, config.WEBHOOK_SECRET):
            return jsonify({"error": "Invalid secret"}), 403

    event = data.get("event", "unknown")
    sheet = data.get("sheet", "unknown")
    row = data.get("row", None)

    print(f"\n🔔 Webhook diterima: event={event}, sheet={sheet}, row={row}")

    # Jalankan sync
    try:
        stats = sync.sync_all_unsynced()
        
        result = {
            "status": "success",
            "message": f"Sync selesai: {stats['success']} berhasil, {stats['failed']} gagal",
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
        sync_history.append(result)
        
        # Simpan max 50 history entries
        if len(sync_history) > 50:
            sync_history.pop(0)
        
        return jsonify(result)

    except Exception as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }
        sync_history.append(error_result)
        return jsonify(error_result), 500


@app.route("/sync", methods=["GET"])
def manual_sync():
    """
    Trigger sync manual via browser.
    Buka URL ini di browser untuk menjalankan sync.
    """
    print("\n🖱️ Manual sync triggered via browser")

    try:
        stats = sync.sync_all_unsynced()

        result = {
            "status": "success",
            "message": f"Sync selesai: {stats['success']} berhasil, {stats['failed']} gagal",
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
        sync_history.append(result)

        if len(sync_history) > 50:
            sync_history.pop(0)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }), 500


@app.route("/history", methods=["GET"])
def history():
    """Lihat sync history."""
    return jsonify({
        "total_syncs": len(sync_history),
        "history": list(reversed(sync_history)),  # Terbaru di atas
    })


@app.route("/dry-run", methods=["GET"])
def dry_run():
    """
    Jalankan sync dalam mode DRY RUN.
    Hanya membaca spreadsheet tanpa membuat card.
    """
    print("\n🔍 Dry run triggered")

    try:
        stats = sync.sync_all_unsynced(dry_run=True)
        return jsonify({
            "status": "success",
            "mode": "dry_run",
            "message": f"Dry run selesai: {stats['total']} baris ditemukan",
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }), 500


def start_server():
    """Jalankan webhook server."""
    port = config.WEBHOOK_PORT

    print(f"""
╔══════════════════════════════════════════════════════╗
║       🤖 Sheets → Trello Sync Bot                   ║
║       Webhook Server                                 ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  Server berjalan di:                                 ║
║  🌐 http://localhost:{port:<5}                          ║
║                                                      ║
║  Endpoints:                                          ║
║  POST /webhook  — Trigger dari Apps Script           ║
║  GET  /sync     — Sync manual via browser            ║
║  GET  /dry-run  — Test tanpa buat card               ║
║  GET  /health   — Health check                       ║
║  GET  /history  — Lihat sync history                 ║
║                                                      ║
║  💡 Gunakan ngrok untuk expose ke internet:           ║
║     ngrok http {port}                                  ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """)

    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    start_server()
