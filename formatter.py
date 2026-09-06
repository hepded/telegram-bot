from app.media import MEDIA_TYPE_LABELS, MEDIA_TYPE_TERMS
from app.search import normalize_text


def format_recommendations(result: dict) -> str:
    source = result["source"]
    recommendations = result["recommendations"]

    if not recommendations:
        return (
            f"Я нашёл произведение: {source['title']}\n"
            "Но пока не смог подобрать похожие варианты."
        )

    source_year = f" ({source['year']})" if source.get("year") else ""
    lines = [
        f"Если тебе понравилось: {source['title']}{source_year}",
        f"Тип: {MEDIA_TYPE_LABELS.get(source['type'], source['type'])}",
        "",
        "Похожие варианты:"
    ]

    for index, item in enumerate(recommendations, start=1):
        year_text = f" ({item['year']})" if item.get("year") else ""
        similarity_percent = round(item["score"] * 100, 1)
        description = item.get("description") or "Описание отсутствует."
        tags = item.get("tags", [])
        genres = [
            genre
            for genre in item.get("genres", [])
            if normalize_text(genre) not in MEDIA_TYPE_TERMS
        ]
        shared_reasons = item.get("shared_reasons", [])

        reason_text = (
            ", ".join(shared_reasons[:4])
            if shared_reasons
            else "похожая атмосфера и общие темы"
        )
        genre_text = ", ".join(genres[:4]) if genres else "не указаны"
        tag_text = ", ".join(tags[:5]) if tags else "не указаны"

        lines.extend([
            "",
            f"{index}. {item['title']}{year_text}",
            f"Сходство: {similarity_percent}%",
            f"Почему может зайти: {reason_text}.",
            f"Жанры: {genre_text}.",
            f"Теги: {tag_text}.",
            f"О чём: {description}"
        ])

    return "\n".join(lines)
