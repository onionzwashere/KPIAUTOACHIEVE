"""
Sync Logic — menghubungkan Google Sheets dengan Trello.
Membaca baris yang belum di-sync dan membuat card untuk masing-masing.
"""

import sys
from datetime import datetime

import config
import google_sheets
import trello_client


def parse_row(row: list[str]) -> dict:
    """
    Parse satu baris spreadsheet menjadi dictionary field card.
    
    Args:
        row: List of string values dari spreadsheet.
    
    Returns:
        Dictionary dengan keys: name, description, labels, due_date
    """
    def safe_get(lst, idx, default=""):
        return lst[idx].strip() if len(lst) > idx else default

    name = safe_get(row, config.COL_NAME)
    description = safe_get(row, config.COL_DESCRIPTION)
    link = safe_get(row, config.COL_LINK)
    list_name = safe_get(row, config.COL_LIST)
    label_str = safe_get(row, config.COL_LABEL)
    due_date = safe_get(row, config.COL_DUE_DATE)

    # Parse labels (bisa dipisahkan dengan koma)
    labels = [l.strip() for l in label_str.split(",") if l.strip()] if label_str else []

    # Validasi due date format
    if due_date:
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            print(f"  ⚠️ Format due date tidak valid: '{due_date}' (harus YYYY-MM-DD), akan diabaikan")
            due_date = ""

    return {
        "name": name,
        "description": description,
        "link": link,
        "list_name": list_name,
        "labels": labels,
        "due_date": due_date,
    }


def sync_row(row_data: list[str], row_index: int, dry_run: bool = False) -> bool:
    """
    Sync satu baris spreadsheet → satu card Trello.
    
    Args:
        row_data: Data baris dari spreadsheet.
        row_index: Index baris di spreadsheet (1-indexed).
        dry_run: Jika True, hanya print tanpa membuat card.
    
    Returns:
        True jika berhasil, False jika gagal.
    """
    parsed = parse_row(row_data)

    if not parsed["name"]:
        print(f"  ⏭️ Baris {row_index}: Nama kosong, dilewati")
        return False

    print(f"  📋 Baris {row_index}: \"{parsed['name']}\"")

    if parsed["description"]:
        print(f"     📝 Deskripsi: {parsed['description'][:50]}{'...' if len(parsed['description']) > 50 else ''}")
    if parsed["link"]:
        print(f"     🔗 Link: {parsed['link']}")
    if parsed["list_name"]:
        print(f"     📋 List: {parsed['list_name']}")
    if parsed["labels"]:
        print(f"     🏷️ Labels: {', '.join(parsed['labels'])}")
    if parsed["due_date"]:
        print(f"     📅 Due date: {parsed['due_date']}")

    # Gabungkan deskripsi dan link menjadi deskripsi card lengkap
    full_description = parsed["description"]
    if parsed["link"]:
        separator = "\n\n---\n" if full_description else ""
        full_description = f"{full_description}{separator}🔗 **Link:** {parsed['link']}"

    # Tentukan target list: dari spreadsheet atau fallback ke .env
    target_list_id = None
    if parsed["list_name"]:
        if not dry_run:
            target_list_id = trello_client.find_or_create_list(
                config.TRELLO_BOARD_ID, parsed["list_name"]
            )
        else:
            print(f"     🔍 [DRY RUN] Akan cari/buat list '{parsed['list_name']}'")
    elif config.TRELLO_LIST_ID:
        target_list_id = config.TRELLO_LIST_ID
    else:
        print(f"     ❌ Tidak ada list target (kolom List kosong & TRELLO_LIST_ID tidak diset)")
        return False

    if dry_run:
        print(f"     🔍 [DRY RUN] Card tidak dibuat")
        return True

    try:
        card = trello_client.create_card(
            name=parsed["name"],
            description=full_description,
            list_id=target_list_id,
            labels=parsed["labels"],
            due_date=parsed["due_date"],
        )
        card_url = card.get("url", "")
        print(f"     ✅ Card dibuat: {card_url}")

        # Update status di spreadsheet
        google_sheets.update_status(row_index, "Synced", card_url)
        print(f"     📝 Status diupdate ke 'Synced'")

        return True

    except Exception as e:
        print(f"     ❌ Gagal membuat card: {e}")
        # Mark sebagai error di spreadsheet
        try:
            google_sheets.update_status(row_index, f"Error: {str(e)[:50]}")
        except Exception:
            pass
        return False


def sync_all_unsynced(dry_run: bool = False) -> dict:
    """
    Sync semua baris yang belum di-sync.
    
    Args:
        dry_run: Jika True, hanya print tanpa membuat card.
    
    Returns:
        Dictionary dengan statistik: total, success, failed, skipped
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"🔄 Sheets → Trello Sync")
    print(f"📅 {timestamp}")
    if dry_run:
        print(f"🔍 Mode: DRY RUN (tidak ada perubahan)")
    print(f"{'='*60}\n")

    stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    try:
        unsynced = google_sheets.get_unsynced_rows()
    except Exception as e:
        print(f"❌ Gagal membaca spreadsheet: {e}")
        return stats

    if not unsynced:
        print("✅ Tidak ada baris baru untuk di-sync!")
        return stats

    print(f"📊 Ditemukan {len(unsynced)} baris yang belum di-sync:\n")
    stats["total"] = len(unsynced)

    for row_index, row_data in unsynced:
        result = sync_row(row_data, row_index, dry_run)
        if result:
            stats["success"] += 1
        else:
            parsed = parse_row(row_data)
            if not parsed["name"]:
                stats["skipped"] += 1
            else:
                stats["failed"] += 1
        print()

    # Print summary
    print(f"{'='*60}")
    print(f"📊 Hasil Sync:")
    print(f"   Total:    {stats['total']}")
    print(f"   ✅ Sukses: {stats['success']}")
    print(f"   ❌ Gagal:  {stats['failed']}")
    print(f"   ⏭️ Skip:   {stats['skipped']}")
    print(f"{'='*60}\n")

    return stats
