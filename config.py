import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_N_RECOMMENDATIONS = 3
DATA_FILE = "app/items.json"
CACHE_FILE = "app/cache_items.json"
USE_ONLINE_SEARCH = True
