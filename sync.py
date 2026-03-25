"""
Sync Logic — menghubungkan Google Sheets dengan Trello.
Membaca task Mahardika dari spreadsheet dan membuat card di Trello.
Format: List = "KPI [BULAN]", Card = judul task, Desc = link pengerjaan.
"""

import sys
from datetime import datetime

import config
import google_sheets
import trello_client


def build_list_name(sheet_name: str) -> str:
    """
    Generate nama list Trello dari nama sheet.
    Contoh: "Febuari 2026 " -> "KPI FEBUARI"
    """
    month = google_sheets.get_month_name_from_sheet(sheet_name)
    prefix = config.TRELLO_LIST_PREFIX
    return f"{prefix} {month}"


def sync_task(task: dict, list_name: str, dry_run: bool = False) -> bool:
    """
    Sync satu task -> satu card Trello.
    
    Args:
        task: Dictionary task dari google_sheets.get_task_data().
        list_name: Nama list Trello (misal: "KPI FEBUARI").
        dry_run: Jika True, hanya print tanpa membuat card.
    
    Returns:
        True jika berhasil, False jika gagal.
    """
    title = task["title"]
    url = task["url"]
    row_index = task["row_index"]

    print(f"  [{row_index}] \"{title}\"")

    if task["date"]:
        print(f"       Tanggal:  {task['date']}")
    if task["sosmed"]:
        print(f"       Platform: {task['sosmed']}")
    if url:
        print(f"       Link:     {url}")
    if task["deadline"]:
        print(f"       Deadline: {task['deadline']}")

    print(f"       -> List:  {list_name}")

    if dry_run:
        print(f"       [DRY RUN] Card tidak dibuat")
        return True

    try:
        # Cari atau buat list
        target_list_id = trello_client.find_or_create_list(
            config.TRELLO_BOARD_ID, list_name
        )

        # Buat card: title = judul task, desc = link pengerjaan
        description = url if url else ""
        card = trello_client.create_card(
            name=title,
            description=description,
            list_id=target_list_id,
        )

        card_url = card.get("url", "")
        print(f"       [OK] Card dibuat: {card_url}")

        # Update result di spreadsheet
        google_sheets.update_result(row_index, "Synced", card_url)
        print(f"       [OK] Result diupdate ke 'Synced'")

        return True

    except Exception as e:
        print(f"       [ERROR] Gagal membuat card: {e}")
        try:
            google_sheets.update_result(row_index, f"Error: {str(e)[:50]}")
        except Exception:
            pass
        return False


def sync_all_unsynced(sheet_name: str = None, dry_run: bool = False) -> dict:
    """
    Sync semua task yang belum di-sync.
    
    Args:
        sheet_name: Nama sheet (default dari config).
        dry_run: Jika True, hanya print tanpa membuat card.
    
    Returns:
        Dictionary dengan statistik: total, success, failed
    """
    target_sheet = sheet_name or config.SHEET_NAME
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n{'='*60}")
    print(f"  Sheets -> Trello Sync")
    print(f"  {timestamp}")
    print(f"  Sheet: {target_sheet}")
    if dry_run:
        print(f"  Mode: DRY RUN (tidak ada perubahan)")
    print(f"{'='*60}\n")

    stats = {"total": 0, "success": 0, "failed": 0}

    try:
        unsynced = google_sheets.get_unsynced_tasks(target_sheet)
    except Exception as e:
        print(f"[ERROR] Gagal membaca spreadsheet: {e}")
        return stats

    if not unsynced:
        print("[OK] Tidak ada task baru untuk di-sync!")
        return stats

    # Generate nama list dari nama sheet
    list_name = build_list_name(target_sheet)
    
    print(f"[INFO] Ditemukan {len(unsynced)} task belum di-sync")
    print(f"[INFO] Target Trello list: \"{list_name}\"\n")
    stats["total"] = len(unsynced)

    for task in unsynced:
        result = sync_task(task, list_name, dry_run)
        if result:
            stats["success"] += 1
        else:
            stats["failed"] += 1
        print()

    # Print summary
    print(f"{'='*60}")
    print(f"  Hasil Sync:")
    print(f"    Total:   {stats['total']}")
    print(f"    Sukses:  {stats['success']}")
    print(f"    Gagal:   {stats['failed']}")
    print(f"{'='*60}\n")

    return stats
