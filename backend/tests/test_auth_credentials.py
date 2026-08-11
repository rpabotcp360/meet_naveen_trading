from app.core.auth import credentials_configured, set_credentials, verify_credentials


def test_set_and_verify_credentials(tmp_path, monkeypatch):
    from keyring.backends.fail import Keyring as FailKeyring
    import keyring
    from app.core import secrets

    monkeypatch.setattr(secrets, "_FALLBACK_PATH", tmp_path / ".secrets.json")
    monkeypatch.setattr(keyring, "get_keyring", lambda: FailKeyring())

    assert not credentials_configured()
    set_credentials("admin", "secret12")
    assert credentials_configured()
    assert verify_credentials("admin", "secret12")
    assert not verify_credentials("admin", "wrong")
    assert not verify_credentials("other", "secret12")
