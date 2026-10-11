import sys
import uuid

import pytest
from conftest import FAKE_KEY

from cae.credential import CredentialManager, WindowsCredentialStore


@pytest.mark.windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows Credential Manager required")
def test_native_credential_roundtrip():
    profile = "test-" + uuid.uuid4().hex
    store = WindowsCredentialStore()
    manager = CredentialManager(store)
    try:
        assert not manager.exists(profile)
        manager.add(FAKE_KEY, profile)
        assert store.read(profile) == FAKE_KEY
        manager.replace(FAKE_KEY + "changed", profile)
        assert store.read(profile) == FAKE_KEY + "changed"
        manager.remove(profile)
        assert not manager.exists(profile)
    finally:
        manager.remove(profile)
