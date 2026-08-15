"""Unit tests for sharding / multitenancy detection (PRD FR-65).

FR-65 is written as "when the upstream analyzer reports
metadata.multitenancy and metadata.shardingProfile…". The external analyzer
emits neither, so these tests pin the alternative the product actually uses:
reading ArangoDB's own collection/database properties.

Fixtures mirror the real driver shapes — ``db.properties()`` returning
``{"sharding": "single"}`` for OneShard, and ``collection.properties()``
returning numberOfShards / shardKeys / replicationFactor / smartGraphAttribute.
"""

from graph_analytics_ai.ai.schema.sharding import detect_sharding_profile


class _FakeCollection:
    def __init__(self, props):
        self._props = props

    def properties(self):
        return self._props


class _FakeDb:
    def __init__(self, collections, db_props=None, fail_on=None):
        self._collections = collections
        self._db_props = db_props or {}
        self._fail_on = fail_on or set()

    def properties(self):
        return self._db_props

    def collections(self):
        return [{"name": name} for name in self._collections]

    def collection(self, name):
        if name in self._fail_on:
            raise RuntimeError(f"collection {name} unavailable")
        return _FakeCollection(self._collections[name])


def test_single_server_reports_no_shard_detail():
    db = _FakeDb({"Person": {}, "knows": {}})

    profile = detect_sharding_profile(db)

    assert profile.deployment_kind == "single_server"
    assert profile.is_one_shard is False
    assert profile.is_multitenant is False
    assert profile.max_number_of_shards == 0


def test_one_shard_database_is_detected_from_db_properties():
    db = _FakeDb(
        {"Person": {"numberOfShards": 1, "shardKeys": ["_key"]}},
        db_props={"sharding": "single"},
    )

    profile = detect_sharding_profile(db)

    assert profile.is_one_shard is True
    assert profile.deployment_kind == "one_shard"
    # A OneShard join stays on one DBServer, so the projection can be local.
    assert profile.gae_projection_hints()["prefer_local_join"] is True


def test_consistent_tenant_shard_key_marks_the_deployment_multitenant():
    db = _FakeDb(
        {
            "Account": {"numberOfShards": 6, "shardKeys": ["tenant_id"]},
            "Transfer": {"numberOfShards": 6, "shardKeys": ["tenant_id"]},
        }
    )

    profile = detect_sharding_profile(db)

    assert profile.deployment_kind == "cluster"
    assert profile.is_multitenant is True
    assert profile.tenant_key == "tenant_id"
    assert profile.max_number_of_shards == 6
    # Cross-tenant analysis on a sharded deployment gets an explicit warning.
    assert any("cross-tenant" in warning for warning in profile.warnings)
    assert profile.gae_projection_hints()["tenant_scoped"] is True


def test_tenant_key_on_only_some_collections_is_not_multitenancy():
    """A key on a subset is a partition strategy, not a tenant boundary.

    Treating it as tenancy would wrongly imply the whole graph is
    tenant-scoped and could make the Copilot scope questions incorrectly.
    """

    db = _FakeDb(
        {
            "Account": {"numberOfShards": 4, "shardKeys": ["tenant_id"]},
            "Reference": {"numberOfShards": 4, "shardKeys": ["region"]},
        }
    )

    profile = detect_sharding_profile(db)

    assert profile.is_multitenant is False
    assert profile.tenant_key is None


def test_default_key_shard_key_is_not_treated_as_a_tenant_key():
    db = _FakeDb({"Person": {"numberOfShards": 3, "shardKeys": ["_key"]}})

    profile = detect_sharding_profile(db)

    assert profile.is_multitenant is False
    assert profile.shard_keys == []


def test_satellite_and_smart_graph_attributes_are_surfaced():
    db = _FakeDb(
        {
            "Lookup": {"numberOfShards": 1, "replicationFactor": "satellite"},
            "Person": {
                "numberOfShards": 3,
                "replicationFactor": 2,
                "smartGraphAttribute": "region",
            },
        }
    )

    profile = detect_sharding_profile(db)

    assert profile.satellite_collections == ["Lookup"]
    assert profile.smart_graph_attributes == ["region"]
    assert profile.min_replication_factor == 2
    assert profile.gae_projection_hints()["satellite_collections"] == ["Lookup"]


def test_system_collections_are_ignored():
    db = _FakeDb(
        {
            "_graphs": {"numberOfShards": 1, "shardKeys": ["tenant_id"]},
            "Person": {},
        }
    )

    profile = detect_sharding_profile(db)

    assert profile.is_multitenant is False


def test_probe_never_raises_and_degrades_to_unknown():
    """A sharding probe must not be able to break schema discovery."""

    class _BrokenDb:
        def properties(self):
            raise RuntimeError("no permission")

        def collections(self):
            raise RuntimeError("no permission")

    profile = detect_sharding_profile(_BrokenDb())

    assert profile.deployment_kind == "unknown"
    assert profile.warnings  # the reason is recorded, not swallowed


def test_one_unreadable_collection_does_not_abort_the_probe():
    db = _FakeDb(
        {
            "Broken": {},
            "Account": {"numberOfShards": 5, "shardKeys": ["tenant_id"]},
            "Transfer": {"numberOfShards": 5, "shardKeys": ["tenant_id"]},
        },
        fail_on={"Broken"},
    )

    profile = detect_sharding_profile(db)

    assert profile.max_number_of_shards == 5
    assert profile.is_multitenant is True
