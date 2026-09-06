from difflib import get_close_matches
from typing import Optional


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def find_exact_title(user_input: str, titles: list) -> Optional[str]:
    normalized_input = normalize_text(user_input)

    for title in titles:
        if normalize_text(title) == normalized_input:
            return title

    return None


def find_close_title(user_input: str, titles: list, cutoff: float = 0.6) -> Optional[str]:
    normalized_input = normalize_text(user_input)

    normalized_map = {
        normalize_text(title): title
        for title in titles
    }

    matches = get_close_matches(
        normalized_input,
        list(normalized_map.keys()),
        n=1,
        cutoff=cutoff
    )

    if matches:
        return normalized_map[matches[0]]

    return None


def find_title(user_input: str, titles: list) -> Optional[str]:
    exact_match = find_exact_title(user_input, titles)
    if exact_match is not None:
        return exact_match

    return find_close_title(user_input, titles)