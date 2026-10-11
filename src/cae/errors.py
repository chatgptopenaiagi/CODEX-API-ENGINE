"""Fixed-message errors: never interpolate backend exceptions or user input."""


class CAEError(Exception):
    code = "engine_error"

    def __init__(self) -> None:
        super().__init__(self.code)


class ConfigurationError(CAEError):
    code = "invalid_configuration"


class CredentialError(CAEError):
    code = "credential_operation_failed"


class CredentialMissing(CredentialError):
    code = "credential_missing"


class CredentialExists(CredentialError):
    code = "credential_already_exists"


class AccessDenied(CAEError):
    code = "access_denied"


class UnsupportedOperation(CAEError):
    code = "unsupported_operation"


class QuotaExceeded(AccessDenied):
    code = "daily_request_limit"


class RateLimitExceeded(AccessDenied):
    code = "request_rate_limit"


class ConcurrentLimitExceeded(AccessDenied):
    code = "concurrent_request_limit"


class AuditError(CAEError):
    code = "audit_unavailable"


class APIError(CAEError):
    code = "api_request_failed"

    def __init__(self, kind: str = "unavailable", status: int | None = None) -> None:
        allowed = {
            "authentication",
            "permission",
            "rate_limit",
            "unavailable",
            "protocol",
            "request",
        }
        self.kind = kind if kind in allowed else "unavailable"
        self.status = status if isinstance(status, int) and 100 <= status <= 599 else None
        super().__init__()
