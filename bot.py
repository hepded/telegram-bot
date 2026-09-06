import asyncio
import logging
import sys
from threading import Lock
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.chat_action import ChatActionSender

from app.config import ADMIN_CHAT_ID, BOT_TOKEN
from app.formatter import format_recommendations
from app.media import clean_media_type_words
from app.recommender import Recommender


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Проверь файл .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
recommender: Recommender | None = None
recommender_lock = Lock()
shown_recommendation_titles_by_chat: dict[int, set[str]] = {}
pending_media_type_choices: dict[int, dict] = {}

MEDIA_TYPE_LABELS = {
    "film": "Фильм",
    "book": "Книга",
    "anime": "Аниме",
    "manga": "Манга"
}

MEDIA_TYPE_BY_ANSWER = {
    "фильм": "film",
    "film": "film",
    "movie": "film",
    "кино": "film",
    "книга": "book",
    "book": "book",
    "роман": "book",
    "аниме": "anime",
    "anime": "anime",
    "манга": "manga",
    "manga": "manga",
    "манхва": "manga",
    "manhwa": "manga"
}


def get_recommender() -> Recommender:
    global recommender

    if recommender is None:
        with recommender_lock:
            if recommender is None:
                recommender = Recommender()

    return recommender


def _build_media_type_keyboard(media_types: list[str]) -> ReplyKeyboardMarkup:
    buttons = [KeyboardButton(text=MEDIA_TYPE_LABELS[media_type]) for media_type in media_types]
    rows = [buttons[index:index + 2] for index in range(0, len(buttons), 2)]
    rows.append([KeyboardButton(text="Отмена")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def _build_user_label(message: Message) -> str:
    user = message.from_user

    if user is None:
        return "unknown-user"

    username = f"@{user.username}" if user.username else "без username"
    full_name = user.full_name.strip() or "Без имени"
    return f"{full_name} ({username}, id={user.id})"


async def notify_admin_about_message(message: Message):
    if not ADMIN_CHAT_ID:
        return

    if message.from_user and str(message.from_user.id) == str(ADMIN_CHAT_ID):
        return

    if not message.text:
        return

    admin_text = (
        "Новое сообщение от пользователя\n\n"
        f"Пользователь: {_build_user_label(message)}\n"
        f"Чат: {message.chat.id}\n\n"
        f"Текст:\n{message.text}"
    )

    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
    except Exception:
        logging.exception("Не удалось отправить сообщение админу")


class UserMessageLoggerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        if event.from_user and event.text:
            logging.info(
                "Сообщение от %s: %s",
                _build_user_label(event),
                event.text
            )
            await notify_admin_about_message(event)

        return await handler(event, data)


dp.message.middleware(UserMessageLoggerMiddleware())


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет. Я подбираю похожие книги, фильмы, аниме и мангу.\n\n"
        "Напиши название произведения, которое тебе понравилось, "
        "и я попробую найти что-то похожее.\n\n"
        "Например:\n"
        "- Death Note\n"
        "- Interstellar\n"
        "- 1984\n"
        "- Berserk"
    )


@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "Как пользоваться ботом:\n\n"
        "1. Отправь название произведения.\n"
        "2. Я найду его в базе.\n"
        "3. Потом предложу похожие варианты.\n\n"
        "Доступные команды:\n"
        "/start — приветствие\n"
        "/help — инструкция\n"
        "/about — о боте\n"
        "/random — случайное произведение\n\n"
    )


@dp.message(Command("about"))
async def about_handler(message: Message):
    await message.answer(
        "Я бот-рекомендатель.\n\n"
        "Помогаю находить похожие книги, фильмы, аниме и мангу "
        "по названию произведения, которое тебе понравилось."
    )


@dp.message(Command("random"))
async def random_handler(message: Message):
    item = await asyncio.to_thread(lambda: get_recommender().get_random_item())

    if item is None:
        await message.answer("База пока пустая.")
        return

    title = item.get("title", "Без названия")
    item_type = item.get("type", "unknown")
    description = item.get("description", "Описание отсутствует.")
    year = item.get("year")

    year_text = f"\nГод: {year}" if year else ""

    await message.answer(
        f"Случайный вариант:\n\n"
        f"Название: {title}\n"
        f"Тип: {item_type}{year_text}\n\n"
        f"Описание:\n{description}"
    )


@dp.message(F.text)
async def recommendation_handler(message: Message):
    user_input = message.text.strip()

    if not user_input:
        await message.answer("Напиши название произведения текстом.")
        return

    async with ChatActionSender.typing(chat_id=message.chat.id, bot=bot):
        pending_choice = pending_media_type_choices.get(message.chat.id)

        if pending_choice:
            normalized_answer = user_input.lower()

            if normalized_answer in ("отмена", "cancel"):
                pending_media_type_choices.pop(message.chat.id, None)
                await message.answer(
                    "Ок, отменил уточнение.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            selected_type = MEDIA_TYPE_BY_ANSWER.get(normalized_answer)
            available_types = pending_choice["media_types"]

            if selected_type not in available_types:
                await message.answer(
                    "Уточни, пожалуйста, что ищем?",
                    reply_markup=_build_media_type_keyboard(available_types)
                )
                return

            pending_media_type_choices.pop(message.chat.id, None)
            user_input = f"{MEDIA_TYPE_LABELS[selected_type]} {pending_choice['title']}"

        else:
            available_types = await asyncio.to_thread(
                lambda: get_recommender().find_available_media_types(user_input)
            )

            if len(available_types) > 1:
                pending_media_type_choices[message.chat.id] = {
                    "title": clean_media_type_words(user_input),
                    "media_types": available_types
                }
                type_labels = ", ".join(MEDIA_TYPE_LABELS[media_type] for media_type in available_types)
                await message.answer(
                    f"Нашёл такое название в нескольких форматах: {type_labels}. Что ищем?",
                    reply_markup=_build_media_type_keyboard(available_types)
                )
                return

        shown_titles = shown_recommendation_titles_by_chat.setdefault(message.chat.id, set())
        result = await asyncio.to_thread(
            lambda: get_recommender().get_recommendations(
                user_input,
                exclude_titles=shown_titles
            )
        )

        if result is None:
            await message.answer(
                "Я не нашёл это произведение в базе.\n"
                "Попробуй другое название."
            )
            return

        response_text = format_recommendations(result)
        await message.answer(response_text, reply_markup=ReplyKeyboardRemove())

        for item in result["recommendations"]:
            shown_titles.add(item["title"])


async def start_polling():
    await dp.start_polling(bot)


def main():
    asyncio.run(start_polling())
