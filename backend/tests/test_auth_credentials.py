from pathlib import Path

from app.core.auth import create_user, get_user, set_credentials, verify_password
from app.storage import database
from app.storage.database import init_db, session_scope


def _init_tmp_db(tmp_path: Path, monkeypatch):
    from app.core.config import get_settings

    get_settings.cache_clear()
    database._engine = None
    monkeypatch.setattr(
        "app.storage.database.get_settings",
        lambda: type(
            "S",
            (),
            {
                "data_dir": tmp_path,
                "log_dir": str(tmp_path / "logs"),
                "log_level": "INFO",
            },
        )(),
    )
    init_db()


def test_signup_and_login_verify(tmp_path, monkeypatch):
    _init_tmp_db(tmp_path, monkeypatch)

    with session_scope() as session:
        assert get_user(session, "alice") is None
        create_user(session, "alice", "secret12")
        user = get_user(session, "alice")
        assert user is not None
        assert verify_password("secret12", user.password_hash)
        assert not verify_password("wrong", user.password_hash)


def test_set_credentials_updates_user(tmp_path, monkeypatch):
    _init_tmp_db(tmp_path, monkeypatch)

    set_credentials("bob", "firstpass")
    set_credentials("bob", "secondpass")
    with session_scope() as session:
        user = get_user(session, "bob")
        assert user is not None
        assert verify_password("secondpass", user.password_hash)
