from flask_caching import Cache
cache_config = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "instance/flask_cache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_OPTIONS": {"mode": 0o700}
}
cache = Cache(config=cache_config)

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()