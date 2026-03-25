"""
Google Sheets Client — membaca dan update data dari spreadsheet.
Menggunakan library gspread dengan Google Service Account.
Mendukung auto-detect kolom dan hyperlink extraction.
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

# Mapping nama header -> key internal (case-insensitive, partial match)
# Urutan penting: dicek dari atas ke bawah
COLUMN_MAPPINGS = {
    "tanggal": "date",
    "link": "title",       # Kolom "Link" berisi judul task + hyperlink
    "sosmed": "sosmed",
    "deadline": "deadline",
    "result": "result",
    "note": "note",
}

# Kolom yang diabaikan (tidak di-parse)
IGNORED_COLUMNS = {"script"}


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

    try:
        return spreadsheet.worksheet(target)
    except gspread.exceptions.WorksheetNotFound:
        pass

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
    """Cari sheet tab yang mengandung keyword bulan (case-insensitive)."""
    tabs = list_sheet_tabs()
    keyword_lower = month_keyword.lower().strip()
    for tab in tabs:
        if keyword_lower in tab.lower().strip():
            return tab
    return None


def detect_columns(header_row: list[str]) -> dict[str, int]:
    """
    Auto-detect posisi kolom berdasarkan nama header.
    Hanya mendeteksi kolom Mahardika (sebelum kolom kedua kosong yang menandakan
    pemisah antar orang).
    
    Args:
        header_row: List of header cell values (baris ke-2 spreadsheet).
    
    Returns:
        Dictionary {key: col_index} misal {"title": 2, "date": 1, "sosmed": 3, ...}
    """
    columns = {}

    # Cari batas kolom Mahardika: mulai dari col 0, berhenti di kolom kosong kedua
    # (kolom A biasanya kosong/nomor, jadi skip kolom kosong pertama)
    found_data = False
    end_index = len(header_row)

    for i, cell in enumerate(header_row):
        cell_clean = cell.strip()
        if cell_clean:
            found_data = True
        elif found_data:
            # Kolom kosong setelah ada data = pemisah antar orang
            end_index = i
            break

    # Detect kolom dalam range Mahardika saja
    for i in range(end_index):
        cell = header_row[i].strip().lower()
        if not cell:
            continue

        # Skip kolom yang diabaikan
        if cell in IGNORED_COLUMNS:
            continue

        # Cari match di COLUMN_MAPPINGS
        for header_key, internal_key in COLUMN_MAPPINGS.items():
            if header_key in cell and internal_key not in columns:
                columns[internal_key] = i
                break

    return columns


def extract_hyperlinks(worksheet: gspread.Worksheet, col_index: int) -> dict[int, str]:
    """
    Ekstraksi hyperlink URL dari kolom tertentu.
    Supports formula HYPERLINK() dan rich-text hyperlinks.
    """
    hyperlinks = {}
    col_letter = chr(ord('A') + col_index)

    # Method 1: Formula HYPERLINK()
    try:
        formulas = worksheet.get(
            f"{col_letter}:{col_letter}",
            value_render_option="FORMULA"
        )
        for i, row_vals in enumerate(formulas, start=1):
            if row_vals:
                cell_val = row_vals[0]
                match = re.match(
                    r'=HYPERLINK\(\s*"([^"]+)"\s*(?:,\s*"[^"]*")?\s*\)',
                    str(cell_val),
                    re.IGNORECASE
                )
                if match:
                    hyperlinks[i] = match.group(1)
    except Exception:
        pass

    # Method 2: Rich-text hyperlinks (Insert > Link)
    try:
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


def get_task_data(sheet_name: str = None) -> list[dict]:
    """
    Ambil data task Mahardika dari spreadsheet.
    Auto-detect kolom dari header row, extract hyperlinks dari kolom title.
    
    Returns:
        List of dict: [{row_index, title, url, date, sosmed, deadline, result, note}, ...]
    """
    worksheet = _get_worksheet(sheet_name)
    all_values = worksheet.get_all_values()

    if len(all_values) <= config.HEADER_ROWS:
        return []

    # Auto-detect kolom dari header row (baris ke-2)
    header_row = all_values[config.HEADER_ROWS - 1]  # 0-indexed
    columns = detect_columns(header_row)

    title_col = columns.get("title")
    if title_col is None:
        raise ValueError(
            f"Kolom 'Link' (judul task) tidak ditemukan di header: {header_row}"
        )

    # Ekstraksi hyperlinks dari kolom title
    hyperlinks = extract_hyperlinks(worksheet, title_col)

    tasks = []
    data_rows = all_values[config.HEADER_ROWS:]

    for i, row in enumerate(data_rows):
        row_index = i + config.HEADER_ROWS + 1  # 1-indexed spreadsheet row

        def safe_get(col_key, default=""):
            idx = columns.get(col_key)
            if idx is None:
                return default
            return row[idx].strip() if len(row) > idx else default

        title = safe_get("title")

        # Skip baris tanpa judul task
        if not title:
            continue

        tasks.append({
            "row_index": row_index,
            "title": title,
            "url": hyperlinks.get(row_index, ""),
            "date": safe_get("date"),
            "sosmed": safe_get("sosmed"),
            "deadline": safe_get("deadline"),
            "result": safe_get("result"),
            "note": safe_get("note"),
        })

    return tasks


def get_unsynced_tasks(sheet_name: str = None) -> list[dict]:
    """Ambil task yang belum di-sync (kolom Result kosong)."""
    all_tasks = get_task_data(sheet_name)
    return [t for t in all_tasks if not t["result"]]


def update_result(row_index: int, result: str = "Synced", card_url: str = "", sheet_name: str = None) -> None:
    """
    Update kolom Result dan (opsional) tambahkan info card Trello di Note.
    Auto-detect posisi kolom dari header row.
    """
    worksheet = _get_worksheet(sheet_name)
    all_values = worksheet.get_all_values()

    if len(all_values) < config.HEADER_ROWS:
        return

    header_row = all_values[config.HEADER_ROWS - 1]
    columns = detect_columns(header_row)

    result_col = columns.get("result")
    if result_col is not None:
        worksheet.update_cell(row_index, result_col + 1, result)

    if card_url:
        note_col = columns.get("note")
        if note_col is not None:
            existing_note = worksheet.cell(row_index, note_col + 1).value or ""
            new_note = f"{existing_note}\n{card_url}".strip() if existing_note else card_url
            worksheet.update_cell(row_index, note_col + 1, new_note)


def get_header_row(sheet_name: str = None) -> list[str]:
    """Ambil header row (baris ke-2 = nama kolom) dari spreadsheet."""
    worksheet = _get_worksheet(sheet_name)
    values = worksheet.row_values(config.HEADER_ROWS)
    return values if values else []


def get_detected_columns_info(sheet_name: str = None) -> dict[str, int]:
    """Return info auto-detected columns untuk debugging/display."""
    header_row = get_header_row(sheet_name)
    return detect_columns(header_row)


def get_month_name_from_sheet(sheet_name: str) -> str:
    """
    Ekstrak nama bulan dari nama sheet.
    Contoh: "Febuari 2026 " -> "FEBUARI", "April 2026" -> "APRIL"
    """
    parts = sheet_name.strip().split()
    if parts:
        return parts[0].upper()
    return sheet_name.strip().upper()
