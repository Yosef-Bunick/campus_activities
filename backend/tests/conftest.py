import os

# Tests never touch dev.db: an in-memory SQLite, set before app.core.config is imported.
os.environ["DATABASE_URL"] = "sqlite://"
