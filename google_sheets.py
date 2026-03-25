"""
Google Sheets Client — membaca dan update data dari spreadsheet.
Menggunakan library gspread dengan Google Service Account.
"""

import gspread
from google.oauth2.service_account import Credentials

import config


# Scopes yang dibutuhkan untuk baca & tulis Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_client() -> gspread.Client:
    """Buat dan return gspread client menggunakan service account credentials."""
    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_PATH,
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def _get_worksheet() -> gspread.Worksheet:
    """Buka worksheet yang dikonfigurasi."""
    client = _get_client()
    spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
    return spreadsheet.worksheet(config.SHEET_NAME)


def get_all_rows() -> list[list[str]]:
    """
    Ambil semua baris dari spreadsheet (tanpa header).
    
    Returns:
        List of rows, dimana setiap row adalah list of string values.
    """
    worksheet = _get_worksheet()
    all_values = worksheet.get_all_values()

    if len(all_values) <= 1:
        return []

    # Skip header row (baris pertama)
    return all_values[1:]


def get_unsynced_rows() -> list[tuple[int, list[str]]]:
    """
    Ambil baris yang belum di-sync (kolom Status kosong).
    
    Returns:
        List of (row_index, row_data) tuples.
        row_index adalah index baris di spreadsheet (1-indexed, termasuk header).
    """
    worksheet = _get_worksheet()
    all_values = worksheet.get_all_values()

    if len(all_values) <= 1:
        return []

    unsynced = []
    for i, row in enumerate(all_values[1:], start=2):  # start=2 karena baris 1 adalah header
        # Pastikan row punya cukup kolom
        name = row[config.COL_NAME].strip() if len(row) > config.COL_NAME else ""
        status = row[config.COL_STATUS].strip() if len(row) > config.COL_STATUS else ""

        # Skip baris kosong (tidak ada nama) atau yang sudah synced
        if name and not status:
            unsynced.append((i, row))

    return unsynced


def get_row_by_index(row_index: int) -> list[str]:
    """
    Ambil data baris berdasarkan index (1-indexed).
    
    Args:
        row_index: Nomor baris di spreadsheet (1-indexed).
    
    Returns:
        List of string values untuk baris tersebut.
    """
    worksheet = _get_worksheet()
    return worksheet.row_values(row_index)


def update_status(row_index: int, status: str = "Synced", card_url: str = "") -> None:
    """
    Update kolom Status dan (opsional) tambahkan URL card Trello.
    
    Args:
        row_index: Nomor baris di spreadsheet (1-indexed).
        status: Status text (default: "Synced").
        card_url: URL card Trello yang dibuat (opsional).
    """
    worksheet = _get_worksheet()

    # Update kolom Status (kolom E = kolom ke-5)
    status_col = config.COL_STATUS + 1  # gspread pakai 1-indexed columns
    worksheet.update_cell(row_index, status_col, status)

    # Jika ada card_url, simpan di kolom setelah Status (kolom F)
    if card_url:
        worksheet.update_cell(row_index, status_col + 1, card_url)


def get_header_row() -> list[str]:
    """Ambil header row (baris pertama) dari spreadsheet."""
    worksheet = _get_worksheet()
    values = worksheet.row_values(1)
    return values if values else []
