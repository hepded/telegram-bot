def normalize_tmdb_movie(movie_data: dict, requested_title: str | None = None) -> dict:
    title = (movie_data.get("title") or "").strip().lower()
    original_title = (movie_data.get("original_title") or "").strip()
    overview = movie_data.get("overview") or "Описание отсутствует."
    release_date = movie_data.get("release_date") or ""

    year = None
    if len(release_date) >= 4 and release_date[:4].isdigit():
        year = int(release_date[:4])

    genre_names = movie_data.get("genre_names", [])

    genres = ["film"]
    genres.extend(genre_names)

    tags = genre_names.copy()
    aliases = []

    for alias in (requested_title, original_title):
        if alias and alias.strip().lower() != title:
            aliases.append(alias.strip())

    return {
        "title": title,
        "aliases": aliases,
        "type": "film",
        "description": overview,
        "tags": tags,
        "genres": genres,
        "year": year
    }


def _append_unique_alias(aliases: list[str], alias: str | None, title: str) -> None:
    if not alias:
        return

    prepared_alias = alias.strip()

    if prepared_alias and prepared_alias.lower() != title and prepared_alias not in aliases:
        aliases.append(prepared_alias)


def _first_sentence_text(value) -> str | None:
    if isinstance(value, list) and value:
        return str(value[0]).strip()

    if isinstance(value, str):
        return value.strip()

    return None


def normalize_openlibrary_book(book_data: dict, requested_title: str | None = None) -> dict:
    title = (book_data.get("title") or "").strip().lower()
    author_names = book_data.get("author_name", [])
    first_sentence = _first_sentence_text(book_data.get("first_sentence"))
    subjects = [
        subject.lower()
        for subject in book_data.get("subject", [])[:8]
        if isinstance(subject, str) and subject.strip()
    ]

    if first_sentence:
        description = first_sentence
    elif author_names:
        description = f"Книга автора: {', '.join(author_names[:3])}."
    else:
        description = "Описание отсутствует."

    aliases = []
    _append_unique_alias(aliases, requested_title, title)

    return {
        "title": title,
        "aliases": aliases,
        "type": "book",
        "description": description,
        "tags": subjects,
        "genres": ["book", *subjects[:5]],
        "year": book_data.get("first_publish_year")
    }


def _jikan_year(media_data: dict, media_type: str) -> int | None:
    year = media_data.get("year")

    if isinstance(year, int):
        return year

    date_field = "aired" if media_type == "anime" else "published"
    from_date = media_data.get(date_field, {}).get("from")

    if isinstance(from_date, str) and len(from_date) >= 4 and from_date[:4].isdigit():
        return int(from_date[:4])

    return None


def normalize_jikan_media(
    media_data: dict,
    media_type: str,
    requested_title: str | None = None
) -> dict:
    title = (
        media_data.get("title_english")
        or media_data.get("title")
        or ""
    ).strip().lower()
    description = media_data.get("synopsis") or "Описание отсутствует."
    tags = []

    for group_name in ("genres", "themes", "demographics"):
        for item in media_data.get(group_name, []):
            name = item.get("name")

            if name:
                tags.append(name.lower())

    aliases = []
    for alias in (
        requested_title,
        media_data.get("title"),
        media_data.get("title_english"),
        media_data.get("title_japanese")
    ):
        _append_unique_alias(aliases, alias, title)

    return {
        "title": title,
        "aliases": aliases,
        "type": media_type,
        "description": description,
        "tags": tags,
        "genres": [media_type, *tags[:5]],
        "year": _jikan_year(media_data, media_type)
    }
