# app/extensions.py
from flask_caching import Cache
cache_config = {
    "CACHE_TYPE": "FileSystemCache", # O "SimpleCache"
    "CACHE_DIR": "instance/flask_cache", # Solo si usas FileSystemCache
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_OPTIONS": {"mode": 0o700} # Solo si usas FileSystemCache
}
cache = Cache(config=cache_config)

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()