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
        google_sheets.update_result(row_index, "Synced", card_url, card_name=title)
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

    stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

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
    print(f"[INFO] Target Trello list: \"{list_name}\"")
    stats["total"] = len(unsynced)

    # Cek duplikat: ambil semua card di Trello saat ini
    existing_cards_map = {}
    try:
        target_list_id = trello_client.find_or_create_list(config.TRELLO_BOARD_ID, list_name)
        existing_cards = trello_client.get_cards_in_list(target_list_id)
        existing_cards_map = {c["name"].strip().lower(): c["url"] for c in existing_cards}
    except Exception as e:
        print(f"[WARNING] Gagal mengecek card yang sudah ada di list Trello, berisiko duplikat: {e}")
    
    # Track judul card yang baru dibuat selama sesi ini untuk handle duplikat dalam satu sheet
    created_this_run = {}

    print(f"[INFO] Memulai sinkronisasi...\n")

    for task in unsynced:
        title = task["title"]
        title_lower = title.strip().lower()
        row_index = task["row_index"]
        
        # Cek apakah card sudah ada di Trello (dari sinkronisasi sebelumnya atau manual)
        if title_lower in existing_cards_map:
            print(f"  [{row_index}] \"{title}\"")
            print(f"       [SKIP] Card sudah ada di Trello (Mencegah Duplikat)")
            if not dry_run:
                try:
                    card_url = existing_cards_map[title_lower]
                    google_sheets.update_result(row_index, "Synced (Auto-Linked)", card_url, card_name=title)
                    print(f"       [OK] Result otomatis diupdate karena Trello Card sudah ada")
                    stats["success"] += 1
                except Exception as e:
                    print(f"       [ERROR] Gagal update Sheet untuk baris duplikat: {e}")
                    stats["failed"] += 1
            else:
                stats["success"] += 1
            stats["skipped"] += 1
            print()
            continue

        # Cek apakah card sudah dibuat pada perulangan for di atas (baris kembar dalam Sheet)
        if title_lower in created_this_run:
            print(f"  [{row_index}] \"{title}\"")
            print(f"       [SKIP] Card dengan judul ini baru saja dibuat (Mencegah Baris Ganda)")
            if not dry_run:
                try:
                    card_url = created_this_run[title_lower]
                    google_sheets.update_result(row_index, "Synced (Duplicate Row)", card_url, card_name=title)
                    stats["success"] += 1
                except Exception as e:
                    print(f"       [ERROR] Gagal update Sheet: {e}")
                    stats["failed"] += 1
            else:
                stats["success"] += 1
            stats["skipped"] += 1
            print()
            continue
            
        # Buat card baru jika lolos cek duplikat
        # sync_task print formatting handlingnya sendiri
        try:
            # Cari atau buat list (sekali lagi memastikan)
            # Sync task logic memanggil trello_client.create_card()
            url_to_use_in_description = task["url"]
            print(f"  [{row_index}] \"{title}\"")
            
            if task["date"]:
                print(f"       Tanggal:  {task['date']}")
            if task["sosmed"]:
                print(f"       Platform: {task['sosmed']}")
                
            if dry_run:
                print(f"       [DRY RUN] Card tidak dibuat (Baru)")
                stats["success"] += 1
                print()
                continue
                
            description = url_to_use_in_description if url_to_use_in_description else ""
            card = trello_client.create_card(
                name=title,
                description=description,
                list_id=target_list_id,
            )
    
            card_url = card.get("url", "")
            print(f"       [OK] Card dibuat: {card_url}")
    
            # Update result di spreadsheet
            google_sheets.update_result(row_index, "Synced", card_url, card_name=title)
            print(f"       [OK] Result diupdate ke 'Synced'")
            
            # Catat baru dibuat agar perulangan for selanjutnya kalau ada judul yang sama tidak duplikat
            created_this_run[title_lower] = card_url
            stats["success"] += 1
            
        except Exception as e:
            print(f"       [ERROR] Gagal membuat card: {e}")
            try:
                google_sheets.update_result(row_index, f"Error: {str(e)[:50]}")
            except Exception:
                pass
            stats["failed"] += 1
            
        print()

    # Print summary
    print(f"{'='*60}")
    print(f"  Hasil Sync:")
    print(f"    Total Target:   {stats['total']}")
    print(f"    Sukses Dibuat/Dihubungkan: {stats['success']}")
    print(f"    Gagal:          {stats['failed']}")
    print(f"    Mencegah Duplikat: {stats['skipped']} baris")
    print(f"{'='*60}\n")

    return stats


def link_existing_tasks(sheet_name: str = None, dry_run: bool = False) -> dict:
    """
    Cari Trello cards yang namanya sama dengan judul task di Google Sheets.
    Jika ketemu, masukkan link card ke kolom Note.
    """
    target_sheet = sheet_name or config.SHEET_NAME
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n{'='*60}")
    print(f"  Link Existing Trello Cards -> Sheets")
    print(f"  {timestamp}")
    print(f"  Sheet: {target_sheet}")
    if dry_run:
        print(f"  Mode: DRY RUN (tidak ada perubahan)")
    print(f"{'='*60}\n")

    stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    try:
        tasks = google_sheets.get_task_data(target_sheet)
    except Exception as e:
        print(f"[ERROR] Gagal membaca spreadsheet: {e}")
        return stats

    if not tasks:
        print("[OK] Tidak ada task ditemukan di Google Sheets.")
        return stats

    list_name = build_list_name(target_sheet)
    print(f"[INFO] Target Trello list: \"{list_name}\"")

    try:
        target_list_id = trello_client.find_or_create_list(config.TRELLO_BOARD_ID, list_name)
        cards = trello_client.get_cards_in_list(target_list_id)
    except Exception as e:
        print(f"[ERROR] Gagal mengambil card dari Trello: {e}")
        return stats
        
    print(f"[INFO] Ditemukan {len(cards)} card di list tersebut.\n")

    # Mapping nama card -> URL card (huruf kecil semua agar case-insensitive)
    trello_cards_map = {c["name"].strip().lower(): c["url"] for c in cards}

    for task in tasks:
        title = task["title"]
        row_index = task["row_index"]
        note = task["note"]
        
        # Jika kolom Note sudah mengandung link Trello, skip
        if "trello.com" in note.lower():
            continue
            
        stats["total"] += 1
        
        # Cari card di Trello yang namanya persis sama dengan judul task
        title_lower = title.strip().lower()
        if title_lower in trello_cards_map:
            card_url = trello_cards_map[title_lower]
            
            print(f"  [{row_index}] \"{title}\"")
            print(f"       -> Match ditemukan: {card_url}")
            
            if dry_run:
                print(f"       [DRY RUN] Kolom Note tidak di-update")
                stats["success"] += 1
            else:
                try:
                    # Update column Result (optional tapi disarankan agar tidak di-sync ganda nanti)
                    result_value = task["result"] if task["result"] else "Synced (Linked)"
                    google_sheets.update_result(row_index, result_value, card_url, card_name=title)
                    print(f"       [OK] Kolom Note berhasil di-update")
                    stats["success"] += 1
                except Exception as e:
                    print(f"       [ERROR] Gagal update Sheet: {e}")
                    stats["failed"] += 1
        else:
            stats["skipped"] += 1

    print(f"\n{'='*60}")
    print(f"  Hasil Pencocokan:")
    print(f"    Target (Note kosong): {stats['total']}")
    print(f"    Berhasil di-link:     {stats['success']}")
    print(f"    Tidak ketemu (Skip):  {stats['skipped']}")
    print(f"    Gagal error:          {stats['failed']}")
    print(f"{'='*60}\n")

    return stats
