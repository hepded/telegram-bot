import json
import shutil
from pathlib import Path


def load_json_list(path: str | Path, *, strict: bool = True) -> list:
    file_path = Path(path)

    if not file_path.exists():
        return []

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    if strict:
        raise ValueError(f"{file_path} должен содержать список объектов")

    return []


def save_json_list(path: str | Path, items: list, *, backup: bool = False) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if backup and file_path.exists():
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        shutil.copy2(file_path, backup_path)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(items, file, ensure_ascii=False, indent=2)
        file.write("\n")
