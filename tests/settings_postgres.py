"""PostgreSQL regression settings for row locking and limit checks."""

import os

from .settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PGDATABASE", "openrouter"),
        "USER": os.environ.get("PGUSER", "postgres"),
        "PASSWORD": os.environ.get("PGPASSWORD", "postgres"),
        "HOST": os.environ.get("PGHOST", "localhost"),
        "PORT": os.environ.get("PGPORT", "5432"),
    }
}
