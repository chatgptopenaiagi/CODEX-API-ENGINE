import json
from unittest.mock import patch

import pytest
from conftest import FAKE_KEY

from cae.cli import main
from cae.errors import APIError, CredentialError
from cae.security import redact


def test_recursive_redaction():
    value = {
        "Authorization": "Bearer hidden",
        "nested": [FAKE_KEY, {"password": "hidden"}],
        FAKE_KEY: "test",
    }
    result = json.dumps(redact(value))
    assert FAKE_KEY not in result and "hidden" not in result
    assert redact(object()) == "[REDACTED]"
    assert redact("Bearer arbitrary") == "[REDACTED]"
    assert redact("opaque-credential", "opaque-credential") == "[REDACTED]"


def test_fixed_error_fields():
    error = APIError(FAKE_KEY, 999)
    assert error.kind == "unavailable" and error.status is None
    assert FAKE_KEY not in repr(error)


def test_cli_status_and_probe_exit(capsys):
    with patch("cae.cli.CAE") as cls:
        cls.return_value.get_status.return_value = {"configured": True}
        assert main(["status"]) == 0
        assert json.loads(capsys.readouterr().out)["configured"]
        cls.return_value.test_connection.return_value = {"authentication": "unknown"}
        assert main(["test"]) == 1
        cls.return_value.test_connection.return_value = {"authentication": "valid"}
        assert main(["test"]) == 0


def test_cli_secret_never_echoed(capsys):
    with (
        patch("cae.cli.CredentialManager") as manager,
        patch("cae.cli.getpass.getpass", return_value=FAKE_KEY),
    ):
        assert main(["add"]) == 0
        manager.return_value.add.assert_called_once_with(FAKE_KEY, "default")
        assert FAKE_KEY not in capsys.readouterr().out
        manager.return_value.add.side_effect = RuntimeError(FAKE_KEY)
        assert main(["add"]) == 1
        assert capsys.readouterr().out.strip() == '{"error": "operation_failed"}'


def test_cli_import_remove_errors(capsys, tmp_path):
    with patch("cae.cli.CredentialManager") as manager:
        assert main(["import", str(tmp_path / "input.txt")]) == 0
        assert main(["remove"]) == 0
        manager.return_value.remove.side_effect = CredentialError()
        assert main(["remove"]) == 1
        assert FAKE_KEY not in capsys.readouterr().out


def test_cli_insecure_getpass_rejected(capsys):
    import getpass
    import warnings

    def insecure(*args):
        warnings.warn("no terminal", getpass.GetPassWarning, stacklevel=2)
        return FAKE_KEY

    with (
        patch("cae.cli.CredentialManager") as manager,
        patch("cae.cli.getpass.getpass", side_effect=insecure),
    ):
        assert main(["add"]) == 1
        manager.return_value.add.assert_not_called()


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == "0.2.0"
