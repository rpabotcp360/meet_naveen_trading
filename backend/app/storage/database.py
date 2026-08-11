from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        db_path = settings.data_dir / "scanner.db"
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _apply_column_migrations(engine)


def _apply_column_migrations(engine) -> None:
    """SQLModel's create_all only creates missing tables, not missing columns.
    Add any columns introduced after a table already existed on disk."""
    migrations = {
        "signals": [
            ("archived", "BOOLEAN DEFAULT 0"),
            ("is_realtime", "BOOLEAN DEFAULT 1"),
            ("outcome", "VARCHAR DEFAULT 'open'"),
        ],
        "watchlist": [
            ("segment_id", "INTEGER"),
        ],
    }
    with engine.begin() as conn:
        for table, columns in migrations.items():
            existing = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))
            }
            for column, ddl_type in columns:
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = Session(get_engine())
    try:
        yield session
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session
