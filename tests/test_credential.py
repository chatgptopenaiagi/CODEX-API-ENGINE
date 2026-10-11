import pytest
from conftest import FAKE_KEY

from cae.credential import CredentialManager
from cae.errors import ConfigurationError, CredentialError, CredentialExists, CredentialMissing


def test_lifecycle(store):
    manager = CredentialManager(store)
    assert not manager.exists()
    manager.add(FAKE_KEY)
    assert manager.exists()
    with pytest.raises(CredentialExists):
        manager.add(FAKE_KEY)
    manager.rotate(FAKE_KEY + "new")
    assert store.read("default") == FAKE_KEY + "new"
    manager.remove()
    manager.remove()
    with pytest.raises(CredentialMissing):
        manager.replace(FAKE_KEY)


@pytest.mark.parametrize(
    "key", ["", "hello", "sk-short", "sk-" + "a" * 2050, "sk-" + "a" * 20 + "\n"]
)
def test_reject_invalid_secret(store, key):
    with pytest.raises(CredentialError) as error:
        CredentialManager(store).add(key)
    assert str(error.value) == "credential_operation_failed"
    assert not store.values


@pytest.mark.parametrize("profile", ["../default", "Default", "a/b", "", "a" * 65])
def test_profile_boundary(store, profile):
    with pytest.raises(ConfigurationError):
        CredentialManager(store).add(FAKE_KEY, profile)


def test_import_retains_original(tmp_path, store):
    path = tmp_path / "input.txt"
    path.write_text(FAKE_KEY + "\n", encoding="utf-8-sig")
    manager = CredentialManager(store)
    manager.import_file(path)
    assert path.exists()
    assert store.read("default") == FAKE_KEY
    manager.import_file(path, replace=True)
    assert list(tmp_path.iterdir()) == [path]


def test_import_failures_are_fixed(tmp_path, store):
    manager = CredentialManager(store)
    path = tmp_path / "input.txt"
    for data in (b"bad", b"x" * 4097, b"\xff"):
        path.write_bytes(data)
        with pytest.raises(CredentialError) as error:
            manager.import_file(path)
        assert error.value.__context__ is None
    with pytest.raises(CredentialError):
        manager.import_file(tmp_path / "absent")


def test_readback_required(store):
    store.read = lambda _: "wrong"
    with pytest.raises(CredentialError):
        CredentialManager(store).add(FAKE_KEY)


def test_no_export(store):
    manager = CredentialManager(store)
    assert not any(hasattr(manager, name) for name in ("export", "get_key", "read"))


def test_profiles_separate(store):
    manager = CredentialManager(store)
    manager.add(FAKE_KEY, "app-a")
    manager.add(FAKE_KEY + "other", "app-b")
    manager.remove("app-a")
    assert manager.exists("app-b")
