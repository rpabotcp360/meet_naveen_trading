from keyring.backends.fail import Keyring as FailKeyring


def test_file_fallback_when_no_keyring(tmp_path, monkeypatch):
    import keyring

    from app.core import secrets

    monkeypatch.setattr(secrets, "_FALLBACK_PATH", tmp_path / ".secrets.json")
    monkeypatch.setattr(keyring, "get_keyring", lambda: FailKeyring())

    assert secrets.get_secret("k") is None
    secrets.set_secret("k", "v")
    assert secrets.get_secret("k") == "v"
    assert secrets.has_secret("k")
    assert (tmp_path / ".secrets.json").exists()
    secrets.delete_secret("k")
    assert secrets.get_secret("k") is None
