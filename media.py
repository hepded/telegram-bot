from app.search import normalize_text


MEDIA_TYPES = ("film", "book", "anime", "manga")
MEDIA_TYPE_TERMS = {
    "film",
    "book",
    "anime",
    "manga",
    "фильм",
    "книга",
    "аниме",
    "манга",
}

MEDIA_TYPE_LABELS = {
    "film": "фильм",
    "book": "книга",
    "anime": "аниме",
    "manga": "манга",
}

TYPE_ALIASES = {
    "film": "film",
    "movie": "film",
    "фильм": "film",
    "films": "film",
    "book": "book",
    "книга": "book",
    "books": "book",
    "роман": "book",
    "anime": "anime",
    "аниме": "anime",
    "manga": "manga",
    "манга": "manga",
    "manhwa": "manga",
    "манхва": "manga",
}

MEDIA_WORDS = set(TYPE_ALIASES)


def normalize_media_type(value: str | None) -> str | None:
    if value is None:
        return None

    return TYPE_ALIASES.get(normalize_text(value))


def requested_media_type(user_input: str) -> str | None:
    normalized_input = normalize_text(user_input)

    for word in normalized_input.split():
        media_type = TYPE_ALIASES.get(word)
        if media_type:
            return media_type

    return None


def clean_media_type_words(user_input: str) -> str:
    normalized_input = normalize_text(user_input)
    words = [
        word
        for word in normalized_input.split()
        if word not in MEDIA_WORDS
    ]
    return " ".join(words) or user_input
