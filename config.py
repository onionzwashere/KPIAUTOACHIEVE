"""
Konfigurasi aplikasi — membaca environment variables dari file .env
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()


def _get_env(key: str, required: bool = True, default: str = None) -> str:
    """Ambil environment variable, raise error jika required dan tidak ada."""
    value = os.getenv(key, default)
    if required and not value:
        print(f"❌ Environment variable '{key}' belum diset!")
        print(f"   Silakan copy .env.example → .env dan isi semua nilai yang dibutuhkan.")
        sys.exit(1)
    return value


# ── Google Sheets ──────────────────────────────────────────────
GOOGLE_CREDENTIALS_PATH = _get_env("GOOGLE_CREDENTIALS_PATH", default="credentials.json")
SPREADSHEET_ID = _get_env("SPREADSHEET_ID")
SHEET_NAME = _get_env("SHEET_NAME", default="Sheet1")

# ── Trello ─────────────────────────────────────────────────────
TRELLO_API_KEY = _get_env("TRELLO_API_KEY")
TRELLO_TOKEN = _get_env("TRELLO_TOKEN")
TRELLO_BOARD_ID = _get_env("TRELLO_BOARD_ID")
TRELLO_LIST_ID = _get_env("TRELLO_LIST_ID", required=False, default="")

# ── Webhook ────────────────────────────────────────────────────
WEBHOOK_SECRET = _get_env("WEBHOOK_SECRET", required=False, default="")
WEBHOOK_PORT = int(_get_env("WEBHOOK_PORT", required=False, default="5000"))

# ── Kolom Spreadsheet (0-indexed) ─────────────────────────────
# Sesuaikan jika format kolom spreadsheet Anda berbeda
COL_NAME = 0         # Kolom A: Nama Card
COL_DESCRIPTION = 1  # Kolom B: Deskripsi
COL_LINK = 2         # Kolom C: Link hasil editan
COL_LIST = 3         # Kolom D: Nama List Trello (auto-create jika belum ada)
COL_LABEL = 4        # Kolom E: Label (opsional)
COL_DUE_DATE = 5     # Kolom F: Due Date (opsional)
COL_STATUS = 6       # Kolom G: Status (auto-filled)
