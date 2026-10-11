import pytest

from cae.errors import CredentialMissing

FAKE_KEY = "sk-" + "synthetic-test-credential-" * 3


class MemoryStore:
    """Test-only backend; never shipped as a production plaintext fallback."""

    def __init__(self):
        self.values = {}
        self.reads = 0

    def read(self, profile):
        self.reads += 1
        if profile not in self.values:
            raise CredentialMissing()
        return self.values[profile]

    def write(self, profile, secret):
        self.values[profile] = secret

    def delete(self, profile):
        self.values.pop(profile, None)

    def exists(self, profile):
        return profile in self.values


@pytest.fixture
def store():
    return MemoryStore()


class FakeTransport:
    def __init__(self, replies=None):
        self.replies = list(replies or [(200, b'{"data":[{"id":"model-for-test"}]}')])
        self.calls = []

    def send(self, method, path, secret, payload):
        self.calls.append((method, path, payload))
        result = self.replies.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
