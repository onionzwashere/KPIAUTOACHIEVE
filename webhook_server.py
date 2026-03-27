"""
Webhook Server — Flask server yang menerima trigger dari Google Apps Script.
Ketika spreadsheet diedit, Apps Script akan mengirim POST request ke server ini,
yang kemudian menjalankan sinkronisasi.
"""

import hmac
import hashlib
import sys
from datetime import datetime

# Fix encoding for Windows console emojis
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, request, jsonify, render_template_string

import config
import sync
import google_sheets

app = Flask(__name__)

# Track sync history
sync_history = []


@app.route("/", methods=["GET"])
def home():
    """Halaman utama — Dashboard Web UI."""
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sheets → Trello Sync Bot</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {
                --primary: #3b82f6;
                --primary-hover: #2563eb;
                --success: #10b981;
                --success-hover: #059669;
                --warning: #f59e0b;
                --warning-hover: #d97706;
                --dark: #1e293b;
                --light: #f8fafc;
                --glass-bg: rgba(255, 255, 255, 0.7);
                --glass-border: rgba(255, 255, 255, 0.5);
            }
            body {
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 0;
                min-height: 100vh;
                background: linear-gradient(135deg, #f0f9ff 0%, #cbebff 100%);
                color: var(--dark);
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            header {
                text-align: center;
                margin-bottom: 40px;
            }
            h1 {
                font-size: 2.5rem;
                font-weight: 700;
                color: var(--primary);
                margin-bottom: 10px;
                text-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .subtitle {
                color: #64748b;
                font-size: 1.1rem;
            }
            .glass-card {
                background: var(--glass-bg);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
                margin-bottom: 30px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }
            h2 {
                margin-top: 0;
                font-size: 1.5rem;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .btn {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                width: 100%;
                padding: 15px 20px;
                border: none;
                border-radius: 12px;
                font-size: 1rem;
                font-weight: 600;
                color: white;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s, background 0.2s;
                margin-bottom: 15px;
            }
            .btn:active {
                transform: scale(0.98);
            }
            .btn-primary { background: var(--primary); box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3); }
            .btn-primary:hover { background: var(--primary-hover); }
            
            .btn-success { background: var(--success); box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); }
            .btn-success:hover { background: var(--success-hover); }
            
            .btn-warning { background: var(--warning); box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3); }
            .btn-warning:hover { background: var(--warning-hover); }
            
            .btn:disabled {
                opacity: 0.7;
                cursor: not-allowed;
                transform: none;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: var(--success);
                box-shadow: 0 0 10px var(--success);
                margin-right: 8px;
            }
            .history-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            .history-table th, .history-table td {
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid rgba(0,0,0,0.05);
            }
            .history-table th {
                font-weight: 600;
                color: #64748b;
                text-transform: uppercase;
                font-size: 0.85rem;
                letter-spacing: 0.05em;
            }
            .history-table tr:last-child td { border-bottom: none; }
            .badge {
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            .badge-success { background: #d1fae5; color: #065f46; }
            .badge-error { background: #fee2e2; color: #991b1b; }
            .badge-info { background: #e0f2fe; color: #075985; }
            
            /* Toast Notification */
            #toast {
                position: fixed;
                bottom: -100px;
                right: 30px;
                min-width: 300px;
                background: white;
                color: var(--dark);
                padding: 15px 20px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 15px;
                transition: bottom 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                z-index: 1000;
                border-left: 5px solid var(--primary);
            }
            #toast.show { bottom: 30px; }
            #toast.success { border-left-color: var(--success); }
            #toast.error { border-left-color: #ef4444; }
            
            .loader {
                border: 3px solid rgba(255,255,255,0.3);
                border-top: 3px solid white;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                animation: spin 1s linear infinite;
                display: none;
            }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            
            .tag {
                display: inline-block;
                padding: 2px 8px;
                background: #f1f5f9;
                border-radius: 4px;
                font-size: 0.8rem;
                color: #475569;
                margin-right: 5px;
                margin-bottom: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1><i class="fa-solid fa-rotate"></i> Sync Bot Dashboard</h1>
                <div class="subtitle">Google Sheets &rarr; Trello Automation</div>
            </header>

            <div class="grid">
                <!-- System Status -->
                <div class="glass-card">
                    <h2><i class="fa-solid fa-server text-primary"></i> System Status</h2>
                    <div style="margin-top: 20px;">
                        <p><span class="status-indicator"></span> <strong>Webhook Server:</strong> Online</p>
                        <p><i class="fa-regular fa-clock" style="color: #64748b; margin-right: 8px;"></i> <strong>Time:</strong> <span id="current-time"></span></p>
                        
                        <div style="margin-top: 20px;">
                            <label for="sheet-selector" style="font-weight: 600; font-size: 0.9rem; color: #64748b; display: block; margin-bottom: 8px;">
                                <i class="fa-regular fa-file-excel"></i> Target Sheet:
                            </label>
                            <select id="sheet-selector" style="width: 100%; padding: 12px 15px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.1); background: rgba(255,255,255,0.8); font-family: inherit; font-size: 1rem; color: var(--dark); cursor: pointer; outline: none; appearance: none; box-shadow: 0 2px 5px rgba(0,0,0,0.02);">
                                <option value="">Loading sheets...</option>
                            </select>
                        </div>

                        <hr style="border: none; border-top: 1px solid rgba(0,0,0,0.05); margin: 20px 0;">
                        <p style="font-size: 0.9rem; color: #64748b;">Bot ini mendengarkan webhook dari Google Scripts secara real-time, atau bisa dijalankan manual melalui tombol di bawah.</p>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="glass-card">
                    <h2><i class="fa-solid fa-bolt" style="color: var(--warning);"></i> Quick Actions</h2>
                    <div style="margin-top: 20px;">
                        <button class="btn btn-success" onclick="triggerAction('/sync', this)">
                            <i class="fa-solid fa-play"></i> <span class="btn-text">Run Normal Sync</span> <div class="loader"></div>
                        </button>
                        <button class="btn btn-primary" onclick="triggerAction('/dry-run', this)">
                            <i class="fa-solid fa-magnifying-glass"></i> <span class="btn-text">Dry Run (Test Only)</span> <div class="loader"></div>
                        </button>
                        <button class="btn btn-warning" onclick="triggerAction('/api/link-existing', this)">
                            <i class="fa-solid fa-link"></i> <span class="btn-text">Link Existing Cards</span> <div class="loader"></div>
                        </button>
                    </div>
                </div>
            </div>

            <!-- History Panel -->
            <div class="glass-card" style="margin-top: 10px;">
                <h2><i class="fa-solid fa-clock-rotate-left" style="color: var(--primary);"></i> Recent Sync History</h2>
                <div style="overflow-x: auto;">
                    <table class="history-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Status</th>
                                <th>Action</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody id="history-body">
                            <tr><td colspan="4" style="text-align: center; color: #64748b;">Loading history...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="toast">
            <i class="fa-solid fa-bell toast-icon" style="font-size: 1.2rem;"></i>
            <div id="toast-message" style="font-weight: 500;">Notification message</div>
        </div>

        <script>
            // Update clock
            setInterval(() => {
                document.getElementById('current-time').innerText = new Date().toLocaleString();
            }, 1000);
            document.getElementById('current-time').innerText = new Date().toLocaleString();

            function showToast(message, type = 'success') {
                const toast = document.getElementById('toast');
                const msgEl = document.getElementById('toast-message');
                const icon = toast.querySelector('.toast-icon');
                
                toast.className = '';
                toast.classList.add('show', type);
                msgEl.innerText = message;
                
                if (type === 'success') icon.className = 'fa-solid fa-circle-check toast-icon';
                else if (type === 'error') icon.className = 'fa-solid fa-circle-exclamation toast-icon';
                else icon.className = 'fa-solid fa-bell toast-icon';
                
                setTimeout(() => toast.classList.remove('show'), 5000);
            }

            async function triggerAction(endpoint, btnElement) {
                const sheetSelector = document.getElementById('sheet-selector');
                const targetSheet = sheetSelector.value;
                if (!targetSheet) {
                    showToast('Harap tunggu hingga daftar sheet selesai dimuat.', 'error');
                    return;
                }
                
                // Construct URL with query param
                const targetUrl = endpoint + '?sheet=' + encodeURIComponent(targetSheet);

                // UI Loading State
                const originalText = btnElement.querySelector('.btn-text').innerText;
                
                btnElement.disabled = true;
                btnElement.querySelector('.btn-text').innerText = 'Processing...';
                btnElement.querySelector('i').style.display = 'none';
                btnElement.querySelector('.loader').style.display = 'block';
                
                try {
                    const res = await fetch(targetUrl, { method: endpoint.includes('/api') ? 'POST' : 'GET' });
                    const data = await res.json();
                    
                    if (res.ok) {
                        showToast(data.message || 'Action completed successfully!', 'success');
                    } else {
                        showToast(data.message || data.error || 'Terjadi kesalahan.', 'error');
                    }
                    loadHistory();
                } catch (e) {
                    showToast('Failed to connect to server.', 'error');
                } finally {
                    btnElement.disabled = false;
                    btnElement.querySelector('.btn-text').innerText = originalText;
                    btnElement.querySelector('i').style.display = 'inline-block';
                    btnElement.querySelector('.loader').style.display = 'none';
                }
            }

            async function loadTabs() {
                try {
                    const res = await fetch('/api/tabs');
                    const data = await res.json();
                    const selector = document.getElementById('sheet-selector');
                    selector.innerHTML = '';
                    
                    if (data.status === 'success' && data.tabs.length > 0) {
                        data.tabs.forEach(tab => {
                            const option = document.createElement('option');
                            option.value = tab;
                            option.innerText = tab;
                            selector.appendChild(option);
                        });
                        // Try to auto-select current month if it exists (Optional polish)
                        const currentMonthStr = new Date().toLocaleString('id-ID', { month: 'long', year: 'numeric' }); // e.g., "Maret 2026"
                        for(let i=0; i < selector.options.length; i++) {
                            if(selector.options[i].value.toLowerCase().includes(currentMonthStr.split(' ')[0].toLowerCase())) {
                                selector.selectedIndex = i;
                                break;
                            }
                        }
                    } else {
                        selector.innerHTML = '<option value="">No sheets found</option>';
                    }
                } catch (e) {
                    console.error('Failed to load tabs', e);
                    const selector = document.getElementById('sheet-selector');
                    selector.innerHTML = '<option value="">Error loading sheets</option>';
                }
            }

            async function loadHistory() {
                try {
                    const res = await fetch('/history');
                    const data = await res.json();
                    const tbody = document.getElementById('history-body');
                    
                    if (!data.history || data.history.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #64748b;">No sync history yet.</td></tr>';
                        return;
                    }
                    
                    tbody.innerHTML = '';
                    data.history.slice(0, 10).forEach(item => {
                        const date = new Date(item.timestamp).toLocaleString();
                        const statusBadge = item.status === 'success' ? '<span class="badge badge-success">Success</span>' : '<span class="badge badge-error">Error</span>';
                        let actionType = '<span class="badge badge-info">' + (item.mode || 'Sync') + '</span>';
                        
                        let details = item.message;
                        if (item.stats) {
                            if (item.stats.skipped !== undefined) {
                                details = `Success: ${item.stats.success} | Skipped: ${item.stats.skipped}`;
                            } else {
                                details = `Success: ${item.stats.success} | Failed: ${item.stats.failed}`;
                            }
                        }
                        
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${date}</td>
                            <td>${statusBadge}</td>
                            <td>${actionType}</td>
                            <td><span style="font-size: 0.9rem;">${details}</span></td>
                        `;
                        tbody.appendChild(tr);
                    });
                } catch (e) {
                    console.error('Failed to load history', e);
                }
            }

            // Initial load
            loadTabs();
            loadHistory();
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)


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

    # Jalankan sync hanya untuk sheet yang diedit
    try:
        if sheet != "unknown":
            stats = sync.sync_all_unsynced(sheet_name=sheet)
        else:
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


@app.route("/api/tabs", methods=["GET"])
def get_tabs():
    """Fetch all available tabs from the spreadsheet."""
    try:
        tabs = google_sheets.list_sheet_tabs()
        return jsonify({"status": "success", "tabs": tabs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/sync", methods=["GET"])
def manual_sync():
    """
    Trigger sync manual via browser.
    Buka URL ini di browser untuk menjalankan sync.
    """
    target_sheet = request.args.get("sheet") or None
    print(f"\n🖱️ Manual sync triggered via browser untuk sheet: {target_sheet}")

    try:
        stats = sync.sync_all_unsynced(sheet_name=target_sheet)

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
    target_sheet = request.args.get("sheet") or None
    print(f"\n🔍 Dry run triggered untuk sheet: {target_sheet}")

    try:
        stats = sync.sync_all_unsynced(sheet_name=target_sheet, dry_run=True)
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


@app.route("/api/link-existing", methods=["POST"])
def api_link_existing():
    """
    Trigger link existing cards manual via browser/UI.
    """
    target_sheet = request.args.get("sheet") or None
    print(f"\n🔗 Link Existing Cards triggered via UI untuk sheet: {target_sheet}")

    try:
        stats = sync.link_existing_tasks(sheet_name=target_sheet)

        result = {
            "status": "success",
            "mode": "link_existing",
            "message": f"Link Existing selesai: {stats['success']} di-link, {stats['skipped']} di-skip.",
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
        sync_history.append(result)

        if len(sync_history) > 50:
            sync_history.pop(0)

        return jsonify(result)

    except Exception as e:
        error_res = {
            "status": "error",
            "mode": "link_existing",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }
        sync_history.append(error_res)
        return jsonify(error_res), 500


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
