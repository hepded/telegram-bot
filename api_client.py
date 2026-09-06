import requests

from app.config import TMDB_BEARER_TOKEN


REQUEST_TIMEOUT = 10
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_DETAILS_URL = "https://api.themoviedb.org/3/movie/{movie_id}"
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
JIKAN_API_URL = "https://api.jikan.moe/v4/{media_type}"
SESSION = requests.Session()


def _get_headers() -> dict:
    if not TMDB_BEARER_TOKEN:
        raise ValueError("Не найден TMDB_BEARER_TOKEN. Проверь файл .env")

    return {
        "Authorization": f"Bearer {TMDB_BEARER_TOKEN}",
        "Accept": "application/json"
    }


def _get_json(url: str, *, headers: dict | None = None, params: dict | None = None) -> dict:
    response = SESSION.get(
        url,
        headers=headers,
        params=params,
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def _first_result(data: dict, key: str) -> dict | None:
    results = data.get(key, [])

    if not results:
        return None

    return results[0]


def search_movie(title: str) -> dict | None:
    if not title.strip():
        return None

    data = _get_json(
        TMDB_SEARCH_URL,
        headers=_get_headers(),
        params={
            "query": title,
            "language": "ru-RU"
        }
    )
    return _first_result(data, "results")


def get_movie_details(movie_id: int) -> dict | None:
    data = _get_json(
        TMDB_MOVIE_DETAILS_URL.format(movie_id=movie_id),
        headers=_get_headers(),
        params={
            "language": "ru-RU"
        }
    )

    genres = data.get("genres", [])
    genre_names = [genre["name"].lower() for genre in genres if "name" in genre]
    data["genre_names"] = genre_names

    return data


def search_book(title: str) -> dict | None:
    if not title.strip():
        return None

    data = _get_json(
        OPEN_LIBRARY_SEARCH_URL,
        headers={
            "User-Agent": "tg-bot-recommender (local development)"
        },
        params={
            "q": title,
            "fields": "key,title,author_name,first_publish_year,subject,first_sentence",
            "limit": 1
        }
    )
    return _first_result(data, "docs")


def _search_jikan_media(title: str, media_type: str) -> dict | None:
    if not title.strip():
        return None

    data = _get_json(
        JIKAN_API_URL.format(media_type=media_type),
        params={
            "q": title,
            "limit": 1,
            "sfw": "true"
        }
    )
    return _first_result(data, "data")


def search_anime(title: str) -> dict | None:
    return _search_jikan_media(title, "anime")


def search_manga(title: str) -> dict | None:
    return _search_jikan_media(title, "manga")
