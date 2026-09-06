import random
import logging

from requests import RequestException
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.cache_manager import add_item_to_cache
from app.config import MODEL_NAME, TOP_N_RECOMMENDATIONS, USE_ONLINE_SEARCH
from app.data_loader import load_items
from app.media import MEDIA_TYPE_TERMS, clean_media_type_words, requested_media_type
from app.media_fetcher import (
    EXACT_CHECKERS,
    candidate_media_loaders,
)
from app.search import find_title, normalize_text


class Recommender:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self._reload_data()

    def _reload_data(self):
        self.items = load_items()
        self.documents = [self._build_document(item) for item in self.items]
        self.normalized_title_sets = [
            self._normalized_titles(item)
            for item in self.items
        ]
        self.title_index, self.title_indexes_by_type = self._build_title_indexes()

        if self.documents:
            self.embeddings = self.model.encode(
                self.documents,
                convert_to_tensor=False
            )
        else:
            self.embeddings = []

    def _build_title_indexes(self) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
        title_index: dict[str, int] = {}
        title_indexes_by_type: dict[str, dict[str, int]] = {}

        for index, item in enumerate(self.items):
            media_type = item.get("type")
            titles = [item["title"], *item.get("aliases", [])]

            for title in titles:
                title_index[title] = index

                if isinstance(media_type, str):
                    title_indexes_by_type.setdefault(media_type, {})[title] = index

        return title_index, title_indexes_by_type

    @staticmethod
    def _build_document(item: dict) -> str:
        description = item.get("description", "")
        tags = " ".join(item.get("tags", []))
        genres = " ".join(item.get("genres", []))
        return f"{description} {tags} {genres}".strip()

    @staticmethod
    def _normalized_titles(item: dict) -> set[str]:
        titles = [item.get("title", ""), *item.get("aliases", [])]
        return {
            normalize_text(title)
            for title in titles
            if title and title.strip()
        }

    @staticmethod
    def _shared_reasons(source_item: dict, candidate: dict) -> list[str]:
        source_terms = {
            normalize_text(term)
            for term in (
                source_item.get("tags", [])
                + source_item.get("genres", [])
            )
            if term and normalize_text(term) not in MEDIA_TYPE_TERMS
        }

        reasons = []
        seen_terms = set()

        for term in candidate.get("tags", []) + candidate.get("genres", []):
            normalized_term = normalize_text(term)

            if not normalized_term or normalized_term in MEDIA_TYPE_TERMS:
                continue

            if normalized_term in source_terms and normalized_term not in seen_terms:
                reasons.append(term)
                seen_terms.add(normalized_term)

        return reasons

    def _find_item_index(self, user_input: str, media_type: str | None = None) -> int | None:
        title_to_index = (
            self.title_indexes_by_type.get(media_type, {})
            if media_type
            else self.title_index
        )

        found_title = find_title(user_input, list(title_to_index.keys()))

        if found_title is not None:
            return title_to_index[found_title]

        return None

    def _find_matching_media_types(self, user_input: str) -> set[str]:
        matching_types: set[str] = set()
        normalized_input = normalize_text(user_input)

        for item, title_set in zip(self.items, self.normalized_title_sets):
            if normalized_input in title_set:
                media_type = item.get("type")
                if isinstance(media_type, str):
                    matching_types.add(media_type)

        return matching_types

    def find_available_media_types(self, user_input: str) -> list[str]:
        if requested_media_type(user_input):
            return []

        cleaned_input = clean_media_type_words(user_input)
        available_types = self._find_matching_media_types(cleaned_input)

        if USE_ONLINE_SEARCH:
            for media_type, checker in EXACT_CHECKERS.items():
                if media_type in available_types:
                    continue

                try:
                    if checker(cleaned_input):
                        available_types.add(media_type)
                except (RequestException, ValueError):
                    logging.info("Не удалось проверить %s для уточнения", media_type)

        type_order = ("film", "book", "anime", "manga")
        return [
            media_type
            for media_type in type_order
            if media_type in available_types
        ]

    def _try_fetch_online(self, user_input: str) -> bool:
        if not USE_ONLINE_SEARCH:
            return False

        for media_type, loader in candidate_media_loaders(requested_media_type(user_input)):
            try:
                normalized_item = loader(user_input)

                if not normalized_item:
                    continue

                add_item_to_cache(normalized_item)
                self._reload_data()
                return True
            except (RequestException, ValueError):
                logging.exception("Не удалось загрузить %s из онлайн API", media_type)

        return False

    def get_recommendations(
        self,
        user_input: str,
        top_n: int | None = None,
        exclude_titles: set[str] | None = None
    ) -> dict | None:
        if top_n is None:
            top_n = TOP_N_RECOMMENDATIONS

        excluded_titles = {
            normalize_text(title)
            for title in (exclude_titles or [])
            if title and title.strip()
        }

        requested_type = requested_media_type(user_input)
        source_index = self._find_item_index(user_input, requested_type)

        if source_index is None:
            source_index = self._find_item_index(
                clean_media_type_words(user_input),
                requested_type
            )

        if source_index is None:
            was_loaded = self._try_fetch_online(user_input)
            if was_loaded:
                source_index = self._find_item_index(
                    clean_media_type_words(user_input),
                    requested_type
                )

        if source_index is None:
            return None

        source_item = self.items[source_index]
        source_type = source_item["type"]
        source_embedding = self.embeddings[source_index]
        source_titles = self.normalized_title_sets[source_index]

        similarities = cosine_similarity(
            [source_embedding],
            self.embeddings
        )[0]

        results = []
        seen_titles = set()

        for index, score in enumerate(similarities):
            if index == source_index:
                continue

            candidate = self.items[index]
            candidate_titles = self.normalized_title_sets[index]

            if candidate["type"] == source_type and source_titles & candidate_titles:
                continue

            if candidate["type"] != source_type:
                continue

            if candidate_titles & excluded_titles:
                continue

            if candidate_titles & seen_titles:
                continue

            seen_titles.update(candidate_titles)

            results.append({
                "title": candidate["title"],
                "type": candidate["type"],
                "description": candidate.get("description", ""),
                "tags": candidate.get("tags", []),
                "genres": candidate.get("genres", []),
                "shared_reasons": self._shared_reasons(source_item, candidate),
                "year": candidate.get("year"),
                "score": float(score)
            })

        results.sort(key=lambda item: item["score"], reverse=True)

        return {
            "source": source_item,
            "recommendations": results[:top_n]
        }

    def get_random_item(self):
        if not self.items:
            return None

        return random.choice(self.items)
