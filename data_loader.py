from app.config import DATA_FILE, CACHE_FILE
from app.storage import load_json_list


def load_items() -> list:
    base_items = load_json_list(DATA_FILE)
    cache_items = load_json_list(CACHE_FILE)

    return base_items + cache_items
