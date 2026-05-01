"""Secret resolution helpers for product metadata.

Product collections store secret references, not resolved secret values. These
helpers resolve references at runtime for operations such as connection tests.
"""

import os
from typing import Dict, Protocol

from .exceptions import ValidationError


class SecretResolver(Protocol):
    """Runtime resolver for product secret references."""

    def resolve(self, secret_ref: Dict[str, str]) -> str:
        """Resolve a secret reference to its secret value."""


class EnvironmentSecretResolver:
    """Resolve `{"kind": "env", "ref": "ENV_VAR"}` secret references."""

    def resolve(self, secret_ref: Dict[str, str]) -> str:
        """Resolve an environment variable secret reference."""

        kind = secret_ref.get("kind")
        ref = secret_ref.get("ref")
        if kind != "env":
            raise ValidationError(f"Unsupported secret reference kind: {kind}")
        if not ref:
            raise ValidationError("Environment secret reference is missing ref")

        value = os.getenv(ref)
        if value is None:
            raise ValidationError(f"Environment secret reference is not set: {ref}")
        return value


class MappingSecretResolver:
    """Resolve secret references from an in-memory mapping.

    This is mainly useful for tests and local embedding scenarios where the API
    host has already obtained secret values from another provider.
    """

    def __init__(self, values: Dict[str, str]):
        """Initialize resolver with values keyed by reference name."""

        self.values = values

    def resolve(self, secret_ref: Dict[str, str]) -> str:
        """Resolve a mapped secret reference."""

        ref = secret_ref.get("ref")
        if not ref:
            raise ValidationError("Secret reference is missing ref")
        try:
            return self.values[ref]
        except KeyError as exc:
            raise ValidationError(f"Secret reference is not available: {ref}") from exc
