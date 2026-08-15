"""Sharding and multitenancy profile detection (PRD FR-65).

The PRD frames FR-65 as "when the upstream analyzer reports
``metadata.multitenancy`` and ``metadata.shardingProfile``, surface them".
The external ``arango-schema-analyzer`` does not emit either field, so that
precondition never holds and the requirement sat blocked.

But the information does not actually need the analyzer: ArangoDB reports it
directly on ``collection.properties()`` (``numberOfShards``, ``shardKeys``,
``distributeShardsLike``, ``replicationFactor``, ``isSmart``, ``smartGraphAttribute``)
and on ``db.properties()`` (``sharding == "single"`` for OneShard). This module
reads those, so the product surfaces a real sharding profile rather than waiting
on an upstream field that may never arrive.

Everything here is best-effort and read-only: single-server deployments simply
report ``deployment_kind == "single_server"`` with no shard detail, and any
driver error degrades to ``unknown`` rather than failing discovery.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Shard-key names that almost always denote a tenant boundary. Used only to
# *suggest* a tenant key for the Requirements Copilot — never to enforce one,
# since a wrong guess would silently scope a user's analysis.
_TENANT_KEY_HINTS = (
    "tenant",
    "tenant_id",
    "tenantid",
    "tenantkey",
    "customer_id",
    "customerid",
    "account_id",
    "accountid",
    "org_id",
    "orgid",
    "organization_id",
    "workspace_id",
)


@dataclass
class ShardingProfile:
    """What the deployment's physical layout implies for analysis."""

    deployment_kind: str = "unknown"
    """``single_server`` | ``cluster`` | ``one_shard`` | ``unknown``."""

    is_one_shard: bool = False
    """OneShard database: every collection lives on one DBServer."""

    is_multitenant: bool = False
    """A consistent non-system shard key looks like a tenant discriminator."""

    tenant_key: Optional[str] = None
    """Inferred tenant field, when ``is_multitenant``. A hint, not a filter."""

    shard_keys: List[str] = field(default_factory=list)
    smart_graph_attributes: List[str] = field(default_factory=list)
    max_number_of_shards: int = 0
    min_replication_factor: Optional[int] = None
    satellite_collections: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_kind": self.deployment_kind,
            "is_one_shard": self.is_one_shard,
            "is_multitenant": self.is_multitenant,
            "tenant_key": self.tenant_key,
            "shard_keys": self.shard_keys,
            "smart_graph_attributes": self.smart_graph_attributes,
            "max_number_of_shards": self.max_number_of_shards,
            "min_replication_factor": self.min_replication_factor,
            "satellite_collections": self.satellite_collections,
            "warnings": self.warnings,
        }

    def gae_projection_hints(self) -> Dict[str, Any]:
        """Projection guidance for the GAE orchestrator (FR-65a).

        OneShard and satellite layouts keep a join local to one DBServer, so a
        projection can be loaded without a cross-server shuffle. This returns
        advice, not configuration — the orchestrator decides what to do with it.
        """

        return {
            "prefer_local_join": self.is_one_shard,
            "shard_aware": self.max_number_of_shards > 1,
            "satellite_collections": self.satellite_collections,
            "tenant_scoped": self.is_multitenant,
            "tenant_key": self.tenant_key,
        }


def detect_sharding_profile(
    db: Any, sample_limit: int = 200
) -> ShardingProfile:
    """Read the deployment's sharding layout from ArangoDB itself.

    Never raises: any driver failure yields an ``unknown`` profile carrying a
    warning, because a sharding probe must not be able to break schema
    discovery.
    """

    profile = ShardingProfile()

    try:
        db_props = _safe_call(db, "properties") or {}
    except Exception as exc:  # noqa: BLE001
        profile.warnings.append(f"database properties unavailable: {exc}")
        db_props = {}

    # OneShard databases report sharding == "single".
    if str(db_props.get("sharding") or "").lower() == "single":
        profile.is_one_shard = True
        profile.deployment_kind = "one_shard"

    try:
        collections = db.collections() or []
    except Exception as exc:  # noqa: BLE001
        profile.warnings.append(f"collection listing unavailable: {exc}")
        profile.deployment_kind = profile.deployment_kind or "unknown"
        return profile

    shard_key_sets: List[List[str]] = []
    saw_shard_info = False

    for entry in collections[:sample_limit]:
        name = entry.get("name") if isinstance(entry, dict) else None
        if not name or str(name).startswith("_"):
            continue
        try:
            props = db.collection(name).properties() or {}
        except Exception:  # noqa: BLE001 — one bad collection must not abort
            continue

        number_of_shards = _as_int(props.get("numberOfShards"))
        if number_of_shards:
            saw_shard_info = True
            profile.max_number_of_shards = max(
                profile.max_number_of_shards, number_of_shards
            )

        replication = props.get("replicationFactor")
        if replication == "satellite":
            profile.satellite_collections.append(str(name))
        else:
            replication_int = _as_int(replication)
            if replication_int:
                profile.min_replication_factor = (
                    replication_int
                    if profile.min_replication_factor is None
                    else min(profile.min_replication_factor, replication_int)
                )

        shard_keys = [
            str(key)
            for key in (props.get("shardKeys") or [])
            # _key is the default shard key and says nothing about tenancy.
            if str(key) not in ("_key",)
        ]
        if shard_keys:
            shard_key_sets.append(sorted(shard_keys))

        smart_attribute = props.get("smartGraphAttribute")
        if smart_attribute:
            profile.smart_graph_attributes.append(str(smart_attribute))

    profile.satellite_collections = sorted(set(profile.satellite_collections))
    profile.smart_graph_attributes = sorted(set(profile.smart_graph_attributes))

    if not profile.deployment_kind or profile.deployment_kind == "unknown":
        if saw_shard_info:
            profile.deployment_kind = "cluster"
        elif collections:
            profile.deployment_kind = "single_server"

    profile.shard_keys = sorted({key for keys in shard_key_sets for key in keys})
    profile.is_multitenant, profile.tenant_key = _infer_tenancy(shard_key_sets)

    if profile.is_multitenant and not profile.is_one_shard:
        profile.warnings.append(
            f"Collections are sharded by {profile.tenant_key!r}; a cross-tenant "
            "analysis will span shards and may mix tenants. Scope the analysis "
            "to one tenant unless that is intended."
        )

    return profile


def _infer_tenancy(shard_key_sets: List[List[str]]) -> tuple[bool, Optional[str]]:
    """Infer a tenant key from shard keys.

    Requires the SAME tenant-looking key on every sharded collection: a key
    present on only some of them is a partition strategy, not a tenant
    boundary, and treating it as one would wrongly imply the whole graph is
    tenant-scoped.
    """

    if not shard_key_sets:
        return False, None

    candidates = [
        {key for key in keys if key.lower() in _TENANT_KEY_HINTS}
        for keys in shard_key_sets
    ]
    if not all(candidates):
        return False, None

    shared = set.intersection(*candidates)
    if not shared:
        return False, None
    return True, sorted(shared)[0]


def _safe_call(target: Any, method_name: str) -> Any:
    method = getattr(target, method_name, None)
    if not callable(method):
        return None
    return method()


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
