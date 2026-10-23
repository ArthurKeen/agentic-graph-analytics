"""Index creation for ArangoDB collections (NFR-12, NFR-19).

NFR-12 requires queries to use indexed workspace, run, timestamp, status and
lineage fields. That requirement was silently unmet on any fresh deployment
until this module existed, because the driver calls it depended on had been
removed. NFR-19 is why the failure path reports specifically rather than
shrugging: a mechanism that cannot run must fail loudly, not quietly do
nothing.


`add_hash_index` and `add_skiplist_index` were removed in python-arango 8, and
`add_persistent_index` is deprecated in favour of `add_index`. This module
provides the one supported path, so a driver upgrade cannot quietly strip
indexing again: there is a single call site to change, and a test can assert
against it.

Both legacy index types map to a **persistent** index. ArangoDB's persistent
index serves equality lookups (what `hash` was for) and range/sort access (what
`skiplist` was for), so the collapse loses nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class IndexSpec:
    """One index to create: which collection, which fields, unique or not."""

    collection: str
    fields: Sequence[str]
    unique: bool = False

    def __str__(self) -> str:
        kind = "unique" if self.unique else "non-unique"
        return f"{self.collection}({', '.join(self.fields)}, {kind})"


def ensure_persistent_indexes(
    db: Any,
    specs: Iterable[IndexSpec],
    *,
    logger: logging.Logger,
    context: str = "indexes",
) -> Tuple[int, List[str]]:
    """Create each index independently; return (created, failures).

    Each index gets its own try/except deliberately. The previous code wrapped
    every index in one `try`, so the first failure skipped all the rest — when
    `add_hash_index` disappeared in python-arango 8, that meant a fresh
    deployment created ZERO secondary indexes while logging that "some" had
    failed. Per-index handling means one bad spec costs one index, and the
    caller can report exactly which.

    Index creation is idempotent server-side: re-creating an existing index is
    a no-op, so this is safe to call on every startup.
    """
    created = 0
    failures: List[str] = []

    for spec in specs:
        try:
            db.collection(spec.collection).add_index(
                {
                    "type": "persistent",
                    "fields": list(spec.fields),
                    "unique": spec.unique,
                }
            )
            created += 1
        except Exception as exc:  # noqa: BLE001 - one failure must not stop the rest
            failures.append(f"{spec}: {type(exc).__name__}: {exc}")

    if failures:
        logger.warning(
            "%s: created %d, failed %d — %s",
            context,
            created,
            len(failures),
            "; ".join(failures),
        )
    else:
        logger.debug("%s: created or confirmed %d index(es)", context, created)

    return created, failures
