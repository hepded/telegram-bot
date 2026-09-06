# Telegram recommender bot

Бот подбирает похожие книги, фильмы, аниме и мангу по названию произведения.

## Что умеет

- Ищет произведение в локальной базе `app/items.json`.
- Если локально ничего не найдено, пробует онлайн-поиск:
  - фильмы: TMDB;
  - книги: Open Library;
  - аниме и манга: Jikan / MyAnimeList.
- Кэширует найденные онлайн произведения в `app/cache_items.json`.
- Показывает 3 похожие рекомендации и не повторяет уже отправленные варианты в рамках запущенного бота.
- Если одно название есть в нескольких форматах, спрашивает, что искать: фильм, книгу, аниме или мангу.
- Для похожести использует модель `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.

## Примеры запросов

```text
Death Note
1984
аниме Death Note
манга Berserk
книга 1984
фильм Interstellar
```

Если написать просто `1984`, бот может уточнить: фильм или книга. Если написать `книга 1984`, он сразу будет искать книгу.

## Требования

- Python 3.11 или новее; локальная среда проекта использует Python 3.14.
- Токен Telegram-бота от @BotFather.
- Интернет для Telegram, онлайн-поиска и первоначальной загрузки модели.

## Настройка

Скопируй шаблон настроек и заполни `.env` в корне проекта:

```bash
cp .env.example .env
```

В Windows PowerShell: `Copy-Item .env.example .env`.

Пример значений:

```env
BOT_TOKEN=telegram_bot_token
ADMIN_CHAT_ID=your_telegram_id
TMDB_BEARER_TOKEN=tmdb_bearer_token
```

`BOT_TOKEN` обязателен. `ADMIN_CHAT_ID` можно оставить пустым: если он задан, бот пересылает туда текст сообщений пользователей, имя, username и идентификаторы пользователя и чата. Текст сообщений и данные пользователя также записываются в консольный лог.

`TMDB_BEARER_TOKEN` нужен для онлайн-поиска фильмов; без него остаются локальная база, Open Library и Jikan. Для Open Library и Jikan токены не нужны. Никогда не публикуй заполненный `.env`.

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Запускай команды из корня проекта. В Windows PowerShell для активации окружения используй `.venv\Scripts\Activate.ps1`.

Модель загружается при первом запросе рекомендаций или `/random`; это может занять время. Зависимости включают PyTorch, поэтому установка требует места на диске. Остановить бота можно через `Ctrl+C`.

Команды бота: `/start`, `/help`, `/about`, `/random`.

## Быстрое заполнение базы

База хранится в `app/items.json`, а онлайн-находки бота дополнительно складываются в `app/cache_items.json`.
Чтобы не добавлять произведения вручную, используй скрипт:

```bash
python scripts/populate_database.py --input seeds.txt
```

Пример `seeds.txt`:

```text
film: Интерстеллар
book: 1984
anime: Тетрадь смерти | Death Note
manga: Берсерк | Berserk
```

Запись через `|` полезна, когда API ищет по английскому названию, а в базе ты хочешь оставить русское.
Например, `anime: Тетрадь смерти | Death Note` будет искать `Death Note`, но сохранит основным названием `тетрадь смерти`, если запустить с `--keep-input-title`.

Можно передать тип сразу для всех строк без префикса:

```bash
python scripts/populate_database.py --type film "The Matrix" "Fight Club"
```

Поддерживаются `.txt`, `.csv` и `.json`. В CSV можно использовать колонки `title,type`, в JSON — список строк или объектов вида `{"title": "Death Note", "type": "anime"}`.

Полезные флаги:

- `--dry-run` — проверить загрузку без изменения файла;
- `--keep-input-title` — оставить твоё название основным, а название из API добавить в алиасы;
- `--cache` — записывать в `app/cache_items.json`;
- `--update` — обновлять уже существующие записи свежими данными из API;
- `--limit 10` — обработать только первые 10 записей.

Для фильмов нужен `TMDB_BEARER_TOKEN` в `.env`; книги, аниме и манга загружаются без токенов.

## Структура проекта

- `run.py` — точка входа.
- `app/bot.py` — Telegram-команды и обработчики сообщений.
- `app/recommender.py` — поиск похожих произведений по эмбеддингам.
- `app/api_client.py` — обращения к внешним API.
- `app/items.json` — основная база произведений, включена в репозиторий.
- `app/cache_items.json` — локальный кэш; создаётся автоматически и не публикуется.
- `scripts/populate_database.py` — наполнение базы.
- `.env.example` — шаблон переменных окружения без секретов.

## Проверка перед публикацией

```bash
python -m compileall -q app scripts run.py
python scripts/populate_database.py --help
```

Эти команды проверяют синтаксис и запуск CLI. Полную работу рекомендаций проверяй вручную после установки зависимостей и настройки токена.

## Публикация на GitHub

Git-репозиторий уже инициализирован с веткой `main`. Создай пустой репозиторий на GitHub (без README, .gitignore и лицензии), затем выполни из корня проекта:

```bash
git add .
git diff --cached --stat
git diff --cached
# После просмотра подготовленных файлов:
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Замени `YOUR_USERNAME` и `YOUR_REPOSITORY` своими значениями. `.gitignore` исключает секреты, виртуальное окружение, кэш, резервные копии и локальные материалы перевода PDF. Эти файлы остаются на компьютере.
