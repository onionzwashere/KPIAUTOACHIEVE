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
        print(f"ERROR: Environment variable '{key}' belum diset!")
        print(f"   Silakan copy .env.example -> .env dan isi semua nilai yang dibutuhkan.")
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

# ── Prefix nama list di Trello ─────────────────────────────────
TRELLO_LIST_PREFIX = _get_env("TRELLO_LIST_PREFIX", required=False, default="KPI")

# ── Kolom Spreadsheet Mahardika (0-indexed) ────────────────────
# Format: | # | Tanggal | Link(task title+hyperlink) | Sosmed | Deadline | Result | Note |
HEADER_ROWS = 2          # Baris 1: nama orang, Baris 2: nama kolom

COL_NUMBER = 0           # Kolom A: Nomor urut
COL_DATE = 1             # Kolom B: Tanggal
COL_TASK_TITLE = 2       # Kolom C: Judul task (display text) + hyperlink URL (link pengerjaan)
COL_SOSMED = 3           # Kolom D: Platform sosmed (Ads, Youtube, Organik, dll)
COL_DEADLINE = 4         # Kolom E: Deadline
COL_RESULT = 5           # Kolom F: Result (on-time / late / kosong jika belum selesai)
COL_NOTE = 6             # Kolom G: Note (catatan tambahan)
