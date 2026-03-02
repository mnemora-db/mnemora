"""Typed exceptions for the Mnemora SDK.

All exceptions inherit from MnemoraError, allowing users to catch
the base class broadly or individual subclasses precisely.

Example::

    from mnemora import MnemoraAuthError, MnemoraNotFoundError

    try:
        state = await client.get_state("agent-1")
    except MnemoraNotFoundError:
        # agent has no stored state yet
        state = None
    except MnemoraAuthError:
        raise  # propagate auth failures
"""

from __future__ import annotations


class MnemoraError(Exception):
    """Base exception for all Mnemora SDK errors.

    Attributes:
        message: Human-readable description of the error.
        code: Machine-readable error code returned by the API (e.g. "NOT_FOUND").
        status_code: HTTP status code that triggered this exception.
    """

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN",
        status_code: int = 0,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"status_code={self.status_code!r})"
        )


class MnemoraAuthError(MnemoraError):
    """Raised when the API returns 401 Unauthorized.

    Check that the API key is correct and has not been revoked.
    """

    def __init__(
        self,
        message: str = "Unauthorized — check your API key.",
        code: str = "UNAUTHORIZED",
    ) -> None:
        super().__init__(message, code=code, status_code=401)


class MnemoraNotFoundError(MnemoraError):
    """Raised when the API returns 404 Not Found.

    The requested resource (agent state, memory item, etc.) does not exist.
    """

    def __init__(
        self,
        message: str = "Resource not found.",
        code: str = "NOT_FOUND",
    ) -> None:
        super().__init__(message, code=code, status_code=404)


class MnemoraConflictError(MnemoraError):
    """Raised when the API returns 409 Conflict.

    Typically caused by an optimistic-locking version mismatch. Re-read
    the current state and retry the update with the latest version number.
    """

    def __init__(
        self,
        message: str = "Conflict — version mismatch. Re-read and retry.",
        code: str = "CONFLICT",
    ) -> None:
        super().__init__(message, code=code, status_code=409)


class MnemoraRateLimitError(MnemoraError):
    """Raised when the API returns 429 Too Many Requests.

    The SDK automatically retries up to max_retries times with exponential
    back-off. This exception is raised only after all retries are exhausted.
    """

    def __init__(
        self,
        message: str = "Rate limited — slow down and retry.",
        code: str = "RATE_LIMITED",
    ) -> None:
        super().__init__(message, code=code, status_code=429)


class MnemoraValidationError(MnemoraError):
    """Raised when the API returns 400 Bad Request.

    The request payload failed server-side validation. Check the message
    for field-level details.
    """

    def __init__(
        self,
        message: str = "Validation error — check request parameters.",
        code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(message, code=code, status_code=400)
