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

