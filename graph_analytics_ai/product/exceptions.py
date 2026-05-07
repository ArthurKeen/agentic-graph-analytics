"""Custom exceptions for product metadata operations."""


class ProductError(Exception):
    """Base exception for product metadata errors."""


class StorageError(ProductError):
    """Raised when product metadata storage fails."""


class ValidationError(ProductError):
    """Raised when product metadata validation fails."""


class NotFoundError(ProductError):
    """Raised when a product metadata entity is not found."""


class DuplicateError(ProductError):
    """Raised when a product metadata entity already exists."""


class ConflictError(ProductError):
    """Raised when an operation conflicts with the current entity state.

    Used (FR-31a AC#8) to reject manual ``PATCH /api/runs/{id}/steps/{id}``
    on agentic runs, where the supervisor is the sole authority on step
    transitions and a UI-driven write would race with the
    ``StepStatusReporter``. The FastAPI adapter maps this to HTTP 409.
    """

