from app.config import CACHE_FILE
from app.storage import load_json_list, save_json_list


def load_cache_items() -> list:
    return load_json_list(CACHE_FILE, strict=False)


def save_cache_items(items: list) -> None:
    save_json_list(CACHE_FILE, items)


def add_item_to_cache(new_item: dict) -> None:
    items = load_cache_items()

    for item in items:
        if item.get("title") == new_item.get("title") and item.get("type") == new_item.get("type"):
            aliases = item.setdefault("aliases", [])

            for alias in new_item.get("aliases", []):
                if alias not in aliases:
                    aliases.append(alias)

            save_cache_items(items)
            return

    items.append(new_item)
    save_cache_items(items)
