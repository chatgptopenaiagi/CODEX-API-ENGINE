import json
import traceback
from unittest.mock import patch

import pytest
from conftest import FAKE_KEY, FakeTransport

from cae.api import MAX_BODY, HTTPSTransport, OpenAIConnector
from cae.errors import APIError, ConfigurationError


@pytest.mark.parametrize(
    "status,kind",
    [
        (401, "authentication"),
        (403, "permission"),
        (429, "rate_limit"),
        (500, "unavailable"),
        (302, "request"),
        (400, "request"),
    ],
)
def test_errors_never_return_body(status, kind):
    connector = OpenAIConnector(FakeTransport([(status, FAKE_KEY.encode())]), retries=0)
    with pytest.raises(APIError) as exc:
        connector.request(FAKE_KEY, "models")
    assert exc.value.kind == kind
    assert FAKE_KEY not in "".join(traceback.format_exception(exc.value))


def test_transport_exception_not_retained():
    connector = OpenAIConnector(FakeTransport([RuntimeError(FAKE_KEY)]), retries=0)
    with pytest.raises(APIError) as exc:
        connector.request(FAKE_KEY, "models")
    assert exc.value.__context__ is None
    assert FAKE_KEY not in repr(exc.value)


def test_get_retry_and_no_generation_retry():
    transport = FakeTransport([(503, b""), (200, b'{"data":[]}')])
    with patch("cae.api.time.sleep"):
        assert OpenAIConnector(transport).request(FAKE_KEY, "models") == {"data": []}
    assert len(transport.calls) == 2
    transport = FakeTransport([(503, b"")])
    with pytest.raises(APIError):
        OpenAIConnector(transport).request(FAKE_KEY, "responses", {})
    assert len(transport.calls) == 1


def test_single_attempt_probe():
    transport = FakeTransport([(429, b"")])
    with pytest.raises(APIError):
        OpenAIConnector(transport).request(FAKE_KEY, "models", single_attempt=True)
    assert len(transport.calls) == 1


@pytest.mark.parametrize("body", [b"oops", b"[]", b"null", b"\xff"])
def test_bad_json(body):
    with pytest.raises(APIError) as error:
        OpenAIConnector(FakeTransport([(200, body)])).request(FAKE_KEY, "models")
    assert error.value.kind == "protocol"
    assert error.value.__context__ is None


def test_output_redaction():
    body = json.dumps({"output": "echo " + FAKE_KEY, "token": "arbitrary"}).encode()
    result = OpenAIConnector(FakeTransport([(200, body)])).request(FAKE_KEY, "responses", {})
    assert FAKE_KEY not in json.dumps(result)
    assert result["token"] == "[REDACTED]"


def test_fixed_origin_and_tls():
    with patch("cae.api.http.client.HTTPSConnection") as cls:
        conn = cls.return_value
        response = conn.getresponse.return_value
        response.status = 200
        response.read.return_value = b'{"data":[]}'
        status, body = HTTPSTransport().send("GET", "/v1/models", FAKE_KEY, None)
        assert status == 200
        assert cls.call_args.args[0] == "api.openai.com"
        context = cls.call_args.kwargs["context"]
        assert context.check_hostname
        assert conn.request.call_args.kwargs["headers"]["Authorization"] == "Bearer " + FAKE_KEY
        conn.close.assert_called_once()


def test_transport_bounds_and_error_sanitization():
    with patch("cae.api.http.client.HTTPSConnection") as cls:
        conn = cls.return_value
        conn.getresponse.return_value.read.return_value = b"x" * (MAX_BODY + 1)
        with pytest.raises(APIError) as exc:
            HTTPSTransport().send("GET", "/v1/models", FAKE_KEY, None)
        assert exc.value.__context__ is None
        conn.close.assert_called_once()
    with pytest.raises(ConfigurationError):
        HTTPSTransport().send("GET", "https://evil.invalid", FAKE_KEY, None)


@pytest.mark.parametrize("value", [-1, 4, 0.5])
def test_retry_limits(value):
    with pytest.raises(ConfigurationError):
        OpenAIConnector(retries=value)


@pytest.mark.parametrize("value", [0, -1, 121, float("nan")])
def test_timeout_limits(value):
    with pytest.raises(ConfigurationError):
        HTTPSTransport(value)
