"""
Trello API Client — membuat card dan mengambil data board/list.
Menggunakan Trello REST API via requests.
"""

import requests

import config


TRELLO_BASE_URL = "https://api.trello.com/1"


def _auth_params() -> dict:
    """Return parameter autentikasi Trello."""
    return {
        "key": config.TRELLO_API_KEY,
        "token": config.TRELLO_TOKEN,
    }


def _make_request(method: str, endpoint: str, params: dict = None, data: dict = None) -> dict:
    """
    Buat HTTP request ke Trello API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE).
        endpoint: API endpoint (misal: /cards).
        params: Query parameters.
        data: Request body data.
    
    Returns:
        Response JSON sebagai dictionary.
    
    Raises:
        Exception: Jika request gagal.
    """
    url = f"{TRELLO_BASE_URL}{endpoint}"
    all_params = {**_auth_params(), **(params or {})}

    response = requests.request(
        method=method,
        url=url,
        params=all_params,
        json=data,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        raise Exception(
            f"Trello API Error [{response.status_code}]: {response.text}"
        )

    return response.json()


# ── Card Operations ────────────────────────────────────────────

def create_card(
    name: str,
    description: str = "",
    list_id: str = None,
    labels: list[str] = None,
    due_date: str = None,
) -> dict:
    """
    Buat card baru di Trello.
    
    Args:
        name: Nama/judul card.
        description: Deskripsi card (markdown supported).
        list_id: ID list tempat card dibuat (default dari config).
        labels: List of label names untuk ditambahkan.
        due_date: Due date dalam format ISO 8601 (YYYY-MM-DD).
    
    Returns:
        Response dictionary dari Trello API (berisi id, url, dll).
    """
    target_list_id = list_id or config.TRELLO_LIST_ID

    params = {
        "name": name,
        "desc": description,
        "idList": target_list_id,
    }

    if due_date:
        params["due"] = due_date

    card = _make_request("POST", "/cards", params=params)

    # Tambahkan labels jika ada
    if labels:
        _add_labels_to_card(card["id"], labels)

    return card


def _add_labels_to_card(card_id: str, label_names: list[str]) -> None:
    """
    Tambahkan labels ke card berdasarkan nama label.
    Labels dicari dari board, jika tidak ada akan dibuat baru.
    """
    # Ambil semua labels yang ada di board
    board_labels = get_board_labels(config.TRELLO_BOARD_ID)
    label_map = {label["name"].lower(): label["id"] for label in board_labels if label["name"]}

    for label_name in label_names:
        label_name_clean = label_name.strip()
        if not label_name_clean:
            continue

        label_id = label_map.get(label_name_clean.lower())

        if label_id:
            # Label sudah ada, tambahkan ke card
            _make_request("POST", f"/cards/{card_id}/idLabels", params={"value": label_id})
        else:
            # Buat label baru dan tambahkan ke card
            new_label = _make_request(
                "POST",
                "/labels",
                params={
                    "name": label_name_clean,
                    "color": "blue",  # Default color
                    "idBoard": config.TRELLO_BOARD_ID,
                },
            )
            _make_request("POST", f"/cards/{card_id}/idLabels", params={"value": new_label["id"]})


# ── Board & List Operations ───────────────────────────────────

def get_boards() -> list[dict]:
    """
    Ambil semua boards milik user.
    
    Returns:
        List of board dictionaries (berisi id, name, url).
    """
    return _make_request("GET", "/members/me/boards", params={"fields": "name,url"})


def get_lists(board_id: str) -> list[dict]:
    """
    Ambil semua lists dalam sebuah board.
    
    Args:
        board_id: ID board Trello.
    
    Returns:
        List of list dictionaries (berisi id, name).
    """
    return _make_request("GET", f"/boards/{board_id}/lists", params={"fields": "name"})


def get_board_labels(board_id: str) -> list[dict]:
    """
    Ambil semua labels dalam sebuah board.
    
    Args:
        board_id: ID board Trello.
    
    Returns:
        List of label dictionaries.
    """
    return _make_request("GET", f"/boards/{board_id}/labels")


# ── List Operations ───────────────────────────────────────────

def create_list(board_id: str, name: str, pos: str = "top") -> dict:
    """
    Buat list baru di board Trello.
    
    Args:
        board_id: ID board Trello.
        name: Nama list baru.
        pos: Posisi list ("top", "bottom", atau angka).
    
    Returns:
        Response dictionary dari Trello API (berisi id, name).
    """
    return _make_request("POST", "/lists", params={
        "name": name,
        "idBoard": board_id,
        "pos": pos,
    })


# Cache untuk lists yang sudah dicari/dibuat dalam session ini
_list_cache: dict[str, str] = {}


def find_or_create_list(board_id: str, list_name: str) -> str:
    """
    Cari list berdasarkan nama. Jika belum ada, buat baru.
    Menggunakan cache untuk menghindari API call berulang.
    
    Args:
        board_id: ID board Trello.
        list_name: Nama list yang dicari/dibuat.
    
    Returns:
        ID list yang ditemukan atau baru dibuat.
    """
    cache_key = f"{board_id}:{list_name.lower().strip()}"

    # Cek cache dulu
    if cache_key in _list_cache:
        return _list_cache[cache_key]

    # Cari di board
    existing_lists = get_lists(board_id)
    for lst in existing_lists:
        if lst["name"].lower().strip() == list_name.lower().strip():
            _list_cache[cache_key] = lst["id"]
            return lst["id"]

    # Belum ada, buat baru
    print(f"     📋 List '{list_name}' belum ada, membuat baru...")
    new_list = create_list(board_id, list_name.strip())
    _list_cache[cache_key] = new_list["id"]
    print(f"     ✅ List '{list_name}' berhasil dibuat (ID: {new_list['id']})")

    return new_list["id"]
