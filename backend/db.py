from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

_client = None
_db     = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(os.getenv("MONGO_URI"))
        _db     = _client["automated_farmer"]
    return _db
