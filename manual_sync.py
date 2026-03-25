"""
Manual Sync — script CLI untuk menjalankan sync manual.
Juga menyediakan utility untuk melihat boards dan lists Trello.
"""

import sys
import argparse

# Parse arguments dulu sebelum import config (untuk --help)
parser = argparse.ArgumentParser(
    description="🤖 Sheets → Trello Sync Bot - Manual Sync Tool",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Contoh penggunaan:
  python manual_sync.py                  # Sync semua baris baru
  python manual_sync.py --dry-run        # Test tanpa buat card
  python manual_sync.py --list-boards    # Lihat daftar board Trello
  python manual_sync.py --list-lists     # Lihat daftar list di board
  python manual_sync.py --check-sheet    # Cek koneksi ke spreadsheet
    """,
)
parser.add_argument("--dry-run", action="store_true", help="Test tanpa membuat card di Trello")
parser.add_argument("--list-boards", action="store_true", help="Tampilkan semua board Trello")
parser.add_argument("--list-lists", action="store_true", help="Tampilkan semua list di board yang dikonfigurasi")
parser.add_argument("--check-sheet", action="store_true", help="Cek koneksi ke Google Sheets")

args = parser.parse_args()

# Import setelah parse args
import config
import google_sheets
import trello_client
import sync


def list_boards():
    """Tampilkan semua board Trello."""
    print("\n📋 Daftar Board Trello:\n")
    try:
        boards = trello_client.get_boards()
        for board in boards:
            print(f"  📌 {board['name']}")
            print(f"     ID:  {board['id']}")
            print(f"     URL: {board.get('url', 'N/A')}")
            print()
        print(f"Total: {len(boards)} boards")
        print(f"\n💡 Copy Board ID ke .env → TRELLO_BOARD_ID")
    except Exception as e:
        print(f"❌ Error: {e}")


def list_lists():
    """Tampilkan semua list di board yang dikonfigurasi."""
    board_id = config.TRELLO_BOARD_ID
    print(f"\n📋 Daftar List di Board {board_id}:\n")
    try:
        lists = trello_client.get_lists(board_id)
        for lst in lists:
            print(f"  📝 {lst['name']}")
            print(f"     ID: {lst['id']}")
            print()
        print(f"Total: {len(lists)} lists")
        print(f"\n💡 Copy List ID ke .env → TRELLO_LIST_ID")
    except Exception as e:
        print(f"❌ Error: {e}")


def check_sheet():
    """Cek koneksi ke Google Sheets."""
    print(f"\n📊 Mengecek koneksi ke spreadsheet...\n")
    try:
        headers = google_sheets.get_header_row()
        print(f"  ✅ Berhasil terhubung!")
        print(f"  📋 Header columns: {headers}")

        all_rows = google_sheets.get_all_rows()
        print(f"  📊 Total baris data: {len(all_rows)}")

        unsynced = google_sheets.get_unsynced_rows()
        print(f"  🔄 Baris belum di-sync: {len(unsynced)}")

        if unsynced:
            print(f"\n  Preview baris yang belum di-sync:")
            for row_idx, row_data in unsynced[:5]:
                name = row_data[config.COL_NAME] if len(row_data) > config.COL_NAME else "(kosong)"
                print(f"    Baris {row_idx}: {name}")
            if len(unsynced) > 5:
                print(f"    ... dan {len(unsynced) - 5} baris lainnya")

    except FileNotFoundError:
        print(f"  ❌ File credentials tidak ditemukan: {config.GOOGLE_CREDENTIALS_PATH}")
        print(f"     Ikuti setup_guide.md untuk mendapatkan credentials.")
    except Exception as e:
        print(f"  ❌ Error: {e}")


def main():
    """Entry point."""
    if args.list_boards:
        list_boards()
    elif args.list_lists:
        list_lists()
    elif args.check_sheet:
        check_sheet()
    else:
        # Run sync
        sync.sync_all_unsynced(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
