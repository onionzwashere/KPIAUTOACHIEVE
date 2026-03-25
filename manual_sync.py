"""
Manual Sync — script CLI untuk menjalankan sync manual.
Juga menyediakan utility untuk melihat boards, lists, dan cek sheet.
"""

import sys
import argparse

# Parse arguments dulu sebelum import config (untuk --help)
parser = argparse.ArgumentParser(
    description="Sheets -> Trello Sync Bot - Manual Sync Tool",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Contoh penggunaan:
  python manual_sync.py                            # Sync semua task baru
  python manual_sync.py --dry-run                  # Test tanpa buat card
  python manual_sync.py --month "Febuari 2026 "    # Sync sheet tertentu
  python manual_sync.py --list-boards              # Lihat daftar board Trello
  python manual_sync.py --list-lists               # Lihat daftar list di board
  python manual_sync.py --check-sheet              # Cek koneksi ke spreadsheet
    """,
)
parser.add_argument("--dry-run", action="store_true", help="Test tanpa membuat card di Trello")
parser.add_argument("--month", type=str, default=None, help="Nama sheet/bulan tertentu (default: dari .env)")
parser.add_argument("--list-boards", action="store_true", help="Tampilkan semua board Trello")
parser.add_argument("--list-lists", action="store_true", help="Tampilkan semua list di board yang dikonfigurasi")
parser.add_argument("--check-sheet", action="store_true", help="Cek koneksi ke Google Sheets")
parser.add_argument("--list-tabs", action="store_true", help="Tampilkan semua tab/sheet yang ada")

args = parser.parse_args()

# Import setelah parse args
import config
import google_sheets
import trello_client
import sync


def list_boards():
    """Tampilkan semua board Trello."""
    print("\n[BOARDS] Daftar Board Trello:\n")
    try:
        boards = trello_client.get_boards()
        for board in boards:
            print(f"  {board['name']}")
            print(f"     ID:  {board['id']}")
            print(f"     URL: {board.get('url', 'N/A')}")
            print()
        print(f"Total: {len(boards)} boards")
        print(f"\nCopy Board ID ke .env -> TRELLO_BOARD_ID")
    except Exception as e:
        print(f"[ERROR] {e}")


def list_lists():
    """Tampilkan semua list di board yang dikonfigurasi."""
    board_id = config.TRELLO_BOARD_ID
    print(f"\n[LISTS] Daftar List di Board {board_id}:\n")
    try:
        lists = trello_client.get_lists(board_id)
        for lst in lists:
            print(f"  {lst['name']}")
            print(f"     ID: {lst['id']}")
            print()
        print(f"Total: {len(lists)} lists")
        print(f"\nCopy List ID ke .env -> TRELLO_LIST_ID")
    except Exception as e:
        print(f"[ERROR] {e}")


def list_tabs():
    """Tampilkan semua sheet tabs di spreadsheet."""
    print(f"\n[TABS] Daftar Sheet Tabs:\n")
    try:
        tabs = google_sheets.list_sheet_tabs()
        for tab in tabs:
            print(f"  - '{tab}'")
        print(f"\nTotal: {len(tabs)} tabs")
    except Exception as e:
        print(f"[ERROR] {e}")


def check_sheet():
    """Cek koneksi ke Google Sheets dan tampilkan data task."""
    target_sheet = args.month or config.SHEET_NAME
    print(f"\n[CHECK] Mengecek koneksi ke spreadsheet...")
    print(f"  Sheet target: '{target_sheet}'\n")
    try:
        headers = google_sheets.get_header_row(target_sheet)
        print(f"  [OK] Berhasil terhubung!")
        print(f"  Header: {headers}")

        tasks = google_sheets.get_task_data(target_sheet)
        print(f"  Total task: {len(tasks)}")

        unsynced = [t for t in tasks if not t["result"]]
        synced = [t for t in tasks if t["result"]]
        print(f"  Belum di-sync: {len(unsynced)}")
        print(f"  Sudah di-sync: {len(synced)}")

        # Generate nama list Trello
        list_name = sync.build_list_name(target_sheet)
        print(f"  Trello list: \"{list_name}\"")

        if tasks:
            print(f"\n  Preview task:")
            for t in tasks[:5]:
                status = f"[{t['result']}]" if t["result"] else "[belum sync]"
                link_info = f" (link: ada)" if t["url"] else " (link: -)"
                print(f"    Baris {t['row_index']}: {t['title']}{link_info} {status}")
            if len(tasks) > 5:
                print(f"    ... dan {len(tasks) - 5} task lainnya")

    except FileNotFoundError:
        print(f"  [ERROR] File credentials tidak ditemukan: {config.GOOGLE_CREDENTIALS_PATH}")
        print(f"     Ikuti setup_guide.md untuk mendapatkan credentials.")
    except Exception as e:
        print(f"  [ERROR] {e}")


def main():
    """Entry point."""
    if args.list_boards:
        list_boards()
    elif args.list_lists:
        list_lists()
    elif args.list_tabs:
        list_tabs()
    elif args.check_sheet:
        check_sheet()
    else:
        # Run sync
        target_sheet = args.month or config.SHEET_NAME
        sync.sync_all_unsynced(sheet_name=target_sheet, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
