from collections.abc import Callable

from app.api_client import (
    get_movie_details,
    search_anime,
    search_book,
    search_manga,
    search_movie,
)
from app.media import clean_media_type_words
from app.normalizer import (
    normalize_jikan_media,
    normalize_openlibrary_book,
    normalize_tmdb_movie,
)
from app.search import normalize_text


def raw_titles_match(user_input: str, *titles: str | None) -> bool:
    normalized_input = normalize_text(user_input)
    return any(
        normalize_text(title) == normalized_input
        for title in titles
        if title
    )


def fetch_movie(user_input: str) -> dict | None:
    cleaned_input = clean_media_type_words(user_input)
    movie = search_movie(cleaned_input)
    if not movie:
        return None

    movie_id = movie.get("id")
    if not movie_id:
        return None

    details = get_movie_details(int(movie_id))
    if not details:
        return None

    return normalize_tmdb_movie(details, requested_title=cleaned_input)


def fetch_book(user_input: str) -> dict | None:
    cleaned_input = clean_media_type_words(user_input)
    book = search_book(cleaned_input)

    if not book:
        return None

    return normalize_openlibrary_book(book, requested_title=cleaned_input)


def fetch_anime(user_input: str) -> dict | None:
    cleaned_input = clean_media_type_words(user_input)
    anime = search_anime(cleaned_input)

    if not anime:
        return None

    return normalize_jikan_media(anime, "anime", requested_title=cleaned_input)


def fetch_manga(user_input: str) -> dict | None:
    cleaned_input = clean_media_type_words(user_input)
    manga = search_manga(cleaned_input)

    if not manga:
        return None

    return normalize_jikan_media(manga, "manga", requested_title=cleaned_input)


MEDIA_LOADERS = {
    "film": fetch_movie,
    "book": fetch_book,
    "anime": fetch_anime,
    "manga": fetch_manga,
}


def fetch_media_item(media_type: str, title: str) -> dict | None:
    return MEDIA_LOADERS[media_type](title)


def has_exact_movie(user_input: str) -> bool:
    movie = search_movie(user_input)
    if not movie:
        return False

    return raw_titles_match(
        user_input,
        movie.get("title"),
        movie.get("original_title"),
    )


def has_exact_book(user_input: str) -> bool:
    book = search_book(user_input)
    if not book:
        return False

    return raw_titles_match(user_input, book.get("title"))


def has_exact_anime(user_input: str) -> bool:
    anime = search_anime(user_input)
    if not anime:
        return False

    return raw_titles_match(
        user_input,
        anime.get("title"),
        anime.get("title_english"),
        anime.get("title_japanese"),
    )


def has_exact_manga(user_input: str) -> bool:
    manga = search_manga(user_input)
    if not manga:
        return False

    return raw_titles_match(
        user_input,
        manga.get("title"),
        manga.get("title_english"),
        manga.get("title_japanese"),
    )


EXACT_CHECKERS = {
    "film": has_exact_movie,
    "book": has_exact_book,
    "anime": has_exact_anime,
    "manga": has_exact_manga,
}


def candidate_media_loaders(requested_type: str | None) -> list[tuple[str, Callable[[str], dict | None]]]:
    if requested_type:
        return [(requested_type, MEDIA_LOADERS[requested_type])]

    return [
        ("film", MEDIA_LOADERS["film"]),
        ("anime", MEDIA_LOADERS["anime"]),
        ("manga", MEDIA_LOADERS["manga"]),
        ("book", MEDIA_LOADERS["book"]),
    ]
