"""
Google Sheets Client — membaca dan update data dari spreadsheet.
Menggunakan library gspread dengan Google Service Account.
Mendukung hyperlink extraction dari kolom task title.
"""

import re
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


def _get_spreadsheet() -> gspread.Spreadsheet:
    """Buka spreadsheet yang dikonfigurasi."""
    client = _get_client()
    return client.open_by_key(config.SPREADSHEET_ID)


def _get_worksheet(sheet_name: str = None) -> gspread.Worksheet:
    """Buka worksheet tertentu atau yang dikonfigurasi. Supports fuzzy matching."""
    spreadsheet = _get_spreadsheet()
    target = sheet_name or config.SHEET_NAME

    # Coba exact match dulu
    try:
        return spreadsheet.worksheet(target)
    except gspread.exceptions.WorksheetNotFound:
        pass

    # Fuzzy match: cari sheet yang namanya cocok setelah di-strip
    target_clean = target.strip().lower()
    for ws in spreadsheet.worksheets():
        if ws.title.strip().lower() == target_clean:
            return ws

    raise gspread.exceptions.WorksheetNotFound(f"Sheet '{target}' tidak ditemukan")


def list_sheet_tabs() -> list[str]:
    """Return daftar nama semua sheet tabs di spreadsheet."""
    spreadsheet = _get_spreadsheet()
    return [ws.title for ws in spreadsheet.worksheets()]


def find_month_sheet(month_keyword: str) -> str | None:
    """
    Cari sheet tab yang mengandung keyword bulan tertentu (case-insensitive).
    Contoh: find_month_sheet("februari") -> "Febuari 2026 "
    
    Returns:
        Nama sheet yang ditemukan, atau None.
    """
    tabs = list_sheet_tabs()
    keyword_lower = month_keyword.lower().strip()
    for tab in tabs:
        if keyword_lower in tab.lower().strip():
            return tab
    return None


def extract_hyperlinks(worksheet: gspread.Worksheet, col_index: int) -> dict[int, str]:
    """
    Ekstraksi hyperlink URL dari kolom tertentu.
    Menggunakan Sheets API untuk mendapatkan hyperlink metadata dan formula HYPERLINK().
    
    Args:
        worksheet: gspread Worksheet object.
        col_index: Index kolom (0-indexed).
    
    Returns:
        Dictionary {row_number(1-indexed): url} untuk setiap cell yang punya hyperlink.
    """
    hyperlinks = {}
    
    # Method 1: Cek formula HYPERLINK() di kolom
    col_letter = chr(ord('A') + col_index)
    try:
        formulas = worksheet.get(
            f"{col_letter}:{col_letter}",
            value_render_option="FORMULA"
        )
        for i, row_vals in enumerate(formulas, start=1):
            if row_vals:
                cell_val = row_vals[0]
                # Parse "=HYPERLINK("url", "text")" formula
                match = re.match(
                    r'=HYPERLINK\(\s*"([^"]+)"\s*(?:,\s*"[^"]*")?\s*\)',
                    str(cell_val),
                    re.IGNORECASE
                )
                if match:
                    hyperlinks[i] = match.group(1)
    except Exception:
        pass

    # Method 2: Gunakan Sheets API langsung untuk mendapatkan rich text hyperlinks
    # (untuk link yang diset via Insert > Link, bukan formula)
    try:
        spreadsheet_id = worksheet.spreadsheet.id
        sheet_id = worksheet.id
        
        # Gunakan internal API client dari gspread
        response = worksheet.spreadsheet.fetch_sheet_metadata(
            params={
                'includeGridData': True,
                'ranges': f"'{worksheet.title}'!{col_letter}:{col_letter}",
                'fields': 'sheets.data.rowData.values(hyperlink,formattedValue)'
            }
        )
        
        sheets_data = response.get('sheets', [])
        if sheets_data:
            grid_data = sheets_data[0].get('data', [])
            if grid_data:
                row_data = grid_data[0].get('rowData', [])
                for i, rd in enumerate(row_data, start=1):
                    values = rd.get('values', [])
                    if values:
                        link = values[0].get('hyperlink', '')
                        if link and i not in hyperlinks:
                            hyperlinks[i] = link
    except Exception:
        pass

    return hyperlinks


def get_all_rows(sheet_name: str = None) -> list[list[str]]:
    """
    Ambil semua baris data dari spreadsheet (skip header rows).
    
    Returns:
        List of rows, dimana setiap row adalah list of string values.
    """
    worksheet = _get_worksheet(sheet_name)
    all_values = worksheet.get_all_values()

    if len(all_values) <= config.HEADER_ROWS:
        return []

    # Skip header rows
    return all_values[config.HEADER_ROWS:]


def get_task_data(sheet_name: str = None) -> list[dict]:
    """
    Ambil data task Mahardika dari spreadsheet, termasuk hyperlink dari kolom task title.
    
    Returns:
        List of dict: [{row_index, title, url, date, sosmed, deadline, result, note}, ...]
    """
    worksheet = _get_worksheet(sheet_name)
    all_values = worksheet.get_all_values()

    if len(all_values) <= config.HEADER_ROWS:
        return []

    # Ekstraksi hyperlinks dari kolom task title
    hyperlinks = extract_hyperlinks(worksheet, config.COL_TASK_TITLE)

    tasks = []
    data_rows = all_values[config.HEADER_ROWS:]

    for i, row in enumerate(data_rows):
        row_index = i + config.HEADER_ROWS + 1  # 1-indexed spreadsheet row

        def safe_get(idx, default=""):
            return row[idx].strip() if len(row) > idx else default

        title = safe_get(config.COL_TASK_TITLE)

        # Skip baris tanpa judul task
        if not title:
            continue

        tasks.append({
            "row_index": row_index,
            "title": title,
            "url": hyperlinks.get(row_index, ""),
            "date": safe_get(config.COL_DATE),
            "sosmed": safe_get(config.COL_SOSMED),
            "deadline": safe_get(config.COL_DEADLINE),
            "result": safe_get(config.COL_RESULT),
            "note": safe_get(config.COL_NOTE),
        })

    return tasks


def get_unsynced_tasks(sheet_name: str = None) -> list[dict]:
    """
    Ambil task yang belum di-sync (kolom Result kosong).
    """
    all_tasks = get_task_data(sheet_name)
    return [t for t in all_tasks if not t["result"]]


def update_result(row_index: int, result: str = "Synced", card_url: str = "", sheet_name: str = None) -> None:
    """
    Update kolom Result dan (opsional) tambahkan info card Trello di Note.
    
    Args:
        row_index: Nomor baris di spreadsheet (1-indexed).
        result: Result text (default: "Synced").
        card_url: URL card Trello yang dibuat (opsional, ditulis di Note).
    """
    worksheet = _get_worksheet(sheet_name)

    # Update kolom Result
    result_col = config.COL_RESULT + 1  # gspread pakai 1-indexed columns
    worksheet.update_cell(row_index, result_col, result)

    # Jika ada card_url, simpan di kolom Note
    if card_url:
        note_col = config.COL_NOTE + 1
        existing_note = worksheet.cell(row_index, note_col).value or ""
        new_note = f"{existing_note}\n{card_url}".strip() if existing_note else card_url
        worksheet.update_cell(row_index, note_col, new_note)


def get_header_row(sheet_name: str = None) -> list[str]:
    """Ambil header row (baris kedua = nama kolom) dari spreadsheet."""
    worksheet = _get_worksheet(sheet_name)
    # Baris ke-2 adalah nama kolom (baris ke-1 adalah nama orang)
    values = worksheet.row_values(config.HEADER_ROWS)
    return values if values else []


def get_month_name_from_sheet(sheet_name: str) -> str:
    """
    Ekstrak nama bulan dari nama sheet.
    Contoh: "Febuari 2026 " -> "FEBUARI"
             "April 2026" -> "APRIL"
    """
    parts = sheet_name.strip().split()
    if parts:
        return parts[0].upper()
    return sheet_name.strip().upper()
