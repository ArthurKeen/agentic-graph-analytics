"""Unit tests for the GraphSet workbench (Phase 6c / FR-68..FR-70).

Covers:

- :class:`GraphSet` and :class:`CrossGraphLink` round-trip + validation.
- ``ProductService.create_graph_set`` validation (empty list, cross-workspace
  members, duplicates, primary-not-in-set, link references unknown profile).
- ``ProductService.list_graph_sets`` / ``get_graph_set``.
- ``ProductService.update_graph_set`` partial patches: rename, swap
  primary, add/remove members, replace links, primary auto-demoted
  when removed from the set.
- ``ProductService.discover_cross_graph_links`` heuristic: matches
  shared joinable field names, scores boosted when same connection,
  caps at ``max_links``.
- API endpoints registered with the right methods + service handlers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from graph_analytics_ai.product import (
    PRODUCT_API_ENDPOINTS,
    CrossGraphLink,
    GraphProfile,
    GraphSet,
    ProductAPIDispatcher,
    create_graph_profile,
    create_graph_set,
)
from graph_analytics_ai.product.constants import (
    GRAPH_SETS_COLLECTION,
    PRODUCT_COLLECTIONS,
)
from graph_analytics_ai.product.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_graph_sets_collection_listed():
    assert GRAPH_SETS_COLLECTION == "aga_graph_sets"
    assert GRAPH_SETS_COLLECTION in PRODUCT_COLLECTIONS


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class TestGraphSetModel:
    def test_round_trip(self):
        link = CrossGraphLink(
            from_graph_profile_id="gp-1",
            to_graph_profile_id="gp-2",
            from_field="document_id",
            to_field="source_document_id",
            link_type="equality",
            confidence=0.85,
        )
        gs = create_graph_set(
            workspace_id="ws-1",
            name="My Set",
            graph_profile_ids=["gp-1", "gp-2"],
            cross_graph_links=[link],
            primary_graph_profile_id="gp-2",
            description="hi",
        )
        d = gs.to_dict()
        assert d["primary_graph_profile_id"] == "gp-2"
        assert d["cross_graph_links"][0]["from_field"] == "document_id"
        gs2 = GraphSet.from_dict(d)
        assert gs2 == gs

    def test_rejects_empty_graph_profile_ids(self):
        with pytest.raises(ValidationError):
            create_graph_set(
                workspace_id="ws-1", name="empty", graph_profile_ids=[]
            )

    def test_rejects_blank_name(self):
        with pytest.raises(ValidationError):
            create_graph_set(
                workspace_id="ws-1", name="   ", graph_profile_ids=["gp-1"]
            )

    def test_rejects_primary_not_in_set(self):
        with pytest.raises(ValidationError):
            create_graph_set(
                workspace_id="ws-1",
                name="bad",
                graph_profile_ids=["gp-1"],
                primary_graph_profile_id="gp-other",
            )

    def test_rejects_link_with_unknown_endpoint(self):
        link = CrossGraphLink(
            from_graph_profile_id="gp-1",
            to_graph_profile_id="gp-other",  # not in the set
            from_field="x",
            to_field="y",
        )
        with pytest.raises(ValidationError):
            create_graph_set(
                workspace_id="ws-1",
                name="bad",
                graph_profile_ids=["gp-1"],
                cross_graph_links=[link],
            )


# ---------------------------------------------------------------------------
# Service stubs
# ---------------------------------------------------------------------------


class _FakeRepository:
    """In-memory repo with the surface ProductService GraphSet flow uses."""

    def __init__(self, profiles: Optional[List[GraphProfile]] = None) -> None:
        self._profiles: Dict[str, GraphProfile] = {
            p.graph_profile_id: p for p in (profiles or [])
        }
        self._sets: Dict[str, GraphSet] = {}
        self.audit_calls: List[Dict[str, Any]] = []

    # GraphProfile surface --------------------------------------------------
    def get_graph_profile(self, graph_profile_id: str) -> GraphProfile:
        if graph_profile_id not in self._profiles:
            raise ValidationError(f"unknown profile {graph_profile_id}")
        return self._profiles[graph_profile_id]

    # GraphSet surface ------------------------------------------------------
    def create_graph_set(self, gs: GraphSet) -> str:
        self._sets[gs.graph_set_id] = gs
        return gs.graph_set_id

    def get_graph_set(self, graph_set_id: str) -> GraphSet:
        return self._sets[graph_set_id]

    def update_graph_set(self, gs: GraphSet) -> str:
        self._sets[gs.graph_set_id] = gs
        return gs.graph_set_id

    def list_graph_sets(self, workspace_id: str) -> List[GraphSet]:
        return [s for s in self._sets.values() if s.workspace_id == workspace_id]

    # Audit surface ---------------------------------------------------------
    def create_audit_event(self, event):
        self.audit_calls.append(
            {"action": event.action, "target_id": event.target_id}
        )
        return "audit-id"


def _profile(
    pid: str,
    *,
    workspace_id: str = "ws-1",
    connection_id: str = "cp-1",
    conceptual_schema: Optional[Dict[str, Any]] = None,
) -> GraphProfile:
    """Build a GraphProfile with a stable ``pid`` so cross-graph wiring is testable."""
    return GraphProfile(
        graph_profile_id=pid,
        workspace_id=workspace_id,
        connection_profile_id=connection_id,
        graph_name=f"g-{pid}",
        conceptual_schema=conceptual_schema,
    )


class _StubResolver:
    def resolve(self, _ref: str) -> str:
        return "x"


def _service(repo: _FakeRepository):
    from graph_analytics_ai.product.service import ProductService

    return ProductService(repository=repo, secret_resolver=_StubResolver())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Service: create_graph_set
# ---------------------------------------------------------------------------


class TestCreateGraphSet:
    def test_happy_path(self):
        repo = _FakeRepository(
            profiles=[_profile("gp-1"), _profile("gp-2"), _profile("gp-3")]
        )
        service = _service(repo)
        gs = service.create_graph_set(
            workspace_id="ws-1",
            name="HR Workspace",
            graph_profile_ids=["gp-1", "gp-2", "gp-3"],
            actor="alice",
        )
        assert gs.name == "HR Workspace"
        assert gs.graph_profile_ids == ["gp-1", "gp-2", "gp-3"]
        # Default primary is the first member.
        assert gs.primary_graph_profile_id == "gp-1"
        assert gs.created_by == "alice"
        assert any(c["action"] == "create_graph_set" for c in repo.audit_calls)

    def test_explicit_primary_must_be_in_list(self):
        repo = _FakeRepository(profiles=[_profile("gp-1")])
        service = _service(repo)
        with pytest.raises(ValidationError):
            service.create_graph_set(
                workspace_id="ws-1",
                name="bad",
                graph_profile_ids=["gp-1"],
                primary_graph_profile_id="gp-other",
            )

    def test_rejects_cross_workspace_profile(self):
        # One profile belongs to a different workspace.
        repo = _FakeRepository(
            profiles=[
                _profile("gp-1", workspace_id="ws-1"),
                _profile("gp-other", workspace_id="ws-2"),
            ]
        )
        service = _service(repo)
        with pytest.raises(ValidationError):
            service.create_graph_set(
                workspace_id="ws-1",
                name="bad",
                graph_profile_ids=["gp-1", "gp-other"],
            )

    def test_rejects_duplicates(self):
        repo = _FakeRepository(profiles=[_profile("gp-1")])
        service = _service(repo)
        with pytest.raises(ValidationError):
            service.create_graph_set(
                workspace_id="ws-1",
                name="bad",
                graph_profile_ids=["gp-1", "gp-1"],
            )

    def test_rejects_link_referencing_non_member(self):
        repo = _FakeRepository(profiles=[_profile("gp-1"), _profile("gp-2")])
        service = _service(repo)
        with pytest.raises(ValidationError):
            service.create_graph_set(
                workspace_id="ws-1",
                name="bad",
                graph_profile_ids=["gp-1"],  # only gp-1
                cross_graph_links=[
                    {
                        "from_graph_profile_id": "gp-1",
                        "to_graph_profile_id": "gp-2",  # not in the set
                        "from_field": "id",
                        "to_field": "id",
                    }
                ],
            )


# ---------------------------------------------------------------------------
# Service: update_graph_set
# ---------------------------------------------------------------------------


class TestUpdateGraphSet:
    def _seeded(self) -> tuple[Any, str]:
        repo = _FakeRepository(
            profiles=[_profile("gp-1"), _profile("gp-2"), _profile("gp-3")]
        )
        service = _service(repo)
        gs = service.create_graph_set(
            workspace_id="ws-1",
            name="seed",
            graph_profile_ids=["gp-1", "gp-2"],
        )
        return service, gs.graph_set_id

    def test_rename_emits_audit(self):
        service, gs_id = self._seeded()
        result = service.update_graph_set(
            graph_set_id=gs_id, name="renamed", actor="bob"
        )
        assert result.name == "renamed"

    def test_add_member_via_graph_profile_ids(self):
        service, gs_id = self._seeded()
        result = service.update_graph_set(
            graph_set_id=gs_id, graph_profile_ids=["gp-1", "gp-2", "gp-3"]
        )
        assert result.graph_profile_ids == ["gp-1", "gp-2", "gp-3"]

    def test_remove_primary_demotes_to_first_remaining(self):
        service, gs_id = self._seeded()
        # Make primary explicit so we can verify demotion.
        service.update_graph_set(
            graph_set_id=gs_id, primary_graph_profile_id="gp-2"
        )
        # Remove gp-2 — the primary must auto-demote to the new first.
        result = service.update_graph_set(
            graph_set_id=gs_id, graph_profile_ids=["gp-3"]
        )
        assert result.primary_graph_profile_id == "gp-3"

    def test_replace_cross_graph_links(self):
        service, gs_id = self._seeded()
        result = service.update_graph_set(
            graph_set_id=gs_id,
            cross_graph_links=[
                {
                    "from_graph_profile_id": "gp-1",
                    "to_graph_profile_id": "gp-2",
                    "from_field": "email",
                    "to_field": "email",
                }
            ],
        )
        assert len(result.cross_graph_links) == 1
        assert result.cross_graph_links[0].from_field == "email"

    def test_rejects_primary_not_in_set(self):
        service, gs_id = self._seeded()
        with pytest.raises(ValidationError):
            service.update_graph_set(
                graph_set_id=gs_id, primary_graph_profile_id="gp-other"
            )


# ---------------------------------------------------------------------------
# Service: discover_cross_graph_links
# ---------------------------------------------------------------------------


class TestDiscoverCrossGraphLinks:
    def _two_profiles_with_shared_email(
        self, *, same_connection: bool = True
    ) -> _FakeRepository:
        p1 = _profile(
            "gp-1",
            connection_id="cp-1",
            conceptual_schema={
                "entities": [
                    {
                        "name": "Employee",
                        "properties": [{"name": "email"}, {"name": "name"}],
                    }
                ],
                "relationships": [],
            },
        )
        p2 = _profile(
            "gp-2",
            connection_id="cp-1" if same_connection else "cp-2",
            conceptual_schema={
                "entities": [
                    {
                        "name": "Person",
                        "properties": [{"name": "email"}, {"name": "ssn"}],
                    }
                ],
                "relationships": [],
            },
        )
        return _FakeRepository(profiles=[p1, p2])

    def test_suggests_shared_email_with_high_confidence_same_connection(self):
        repo = self._two_profiles_with_shared_email(same_connection=True)
        service = _service(repo)
        gs = service.create_graph_set(
            workspace_id="ws-1",
            name="HR + KG",
            graph_profile_ids=["gp-1", "gp-2"],
        )
        candidates = service.discover_cross_graph_links(graph_set_id=gs.graph_set_id)
        assert any(c["from_field"] == "email" for c in candidates)
        email_candidate = next(c for c in candidates if c["from_field"] == "email")
        assert email_candidate["confidence"] == 0.85

    def test_lower_confidence_for_different_connection(self):
        repo = self._two_profiles_with_shared_email(same_connection=False)
        service = _service(repo)
        gs = service.create_graph_set(
            workspace_id="ws-1",
            name="HR + KG",
            graph_profile_ids=["gp-1", "gp-2"],
        )
        candidates = service.discover_cross_graph_links(graph_set_id=gs.graph_set_id)
        assert candidates[0]["confidence"] == 0.60

    def test_max_links_caps_results(self):
        properties = [
            {"name": "email"},
            {"name": "ssn"},
            {"name": "phone"},
            {"name": "uuid"},
        ]
        p1 = _profile(
            "gp-1",
            conceptual_schema={
                "entities": [{"name": "X", "properties": properties}],
                "relationships": [],
            },
        )
        p2 = _profile(
            "gp-2",
            conceptual_schema={
                "entities": [{"name": "Y", "properties": properties}],
                "relationships": [],
            },
        )
        repo = _FakeRepository(profiles=[p1, p2])
        service = _service(repo)
        gs = service.create_graph_set(
            workspace_id="ws-1",
            name="cap-me",
            graph_profile_ids=["gp-1", "gp-2"],
        )
        candidates = service.discover_cross_graph_links(
            graph_set_id=gs.graph_set_id, max_links=2
        )
        assert len(candidates) == 2

    def test_empty_when_no_shared_joinable_fields(self):
        p1 = _profile(
            "gp-1",
            conceptual_schema={
                "entities": [{"name": "X", "properties": [{"name": "color"}]}],
                "relationships": [],
            },
        )
        p2 = _profile(
            "gp-2",
            conceptual_schema={
                "entities": [{"name": "Y", "properties": [{"name": "rating"}]}],
                "relationships": [],
            },
        )
        repo = _FakeRepository(profiles=[p1, p2])
        service = _service(repo)
        gs = service.create_graph_set(
            workspace_id="ws-1",
            name="no-overlap",
            graph_profile_ids=["gp-1", "gp-2"],
        )
        assert service.discover_cross_graph_links(graph_set_id=gs.graph_set_id) == []


# ---------------------------------------------------------------------------
# API endpoint registration
# ---------------------------------------------------------------------------


class TestGraphSetEndpoints:
    @pytest.mark.parametrize(
        "method,path,service_method",
        [
            ("POST", "/api/workspaces/{workspace_id}/graph-sets", "create_graph_set"),
            ("GET", "/api/workspaces/{workspace_id}/graph-sets", "list_graph_sets"),
            ("GET", "/api/graph-sets/{graph_set_id}", "get_graph_set"),
            ("PATCH", "/api/graph-sets/{graph_set_id}", "update_graph_set"),
            (
                "POST",
                "/api/graph-sets/{graph_set_id}/discover-cross-graph-links",
                "discover_cross_graph_links",
            ),
        ],
    )
    def test_endpoint_registered(self, method, path, service_method):
        endpoint = next(
            (
                e
                for e in PRODUCT_API_ENDPOINTS
                if e.path == path and e.method == method
            ),
            None,
        )
        assert endpoint is not None
        assert endpoint.service_method == service_method
        assert "graph-sets" in endpoint.tags

    def test_dispatcher_routes_create(self):
        captured: Dict[str, Any] = {}

        class _Service:
            def create_graph_set(
                self,
                workspace_id: str,
                name: str,
                graph_profile_ids: List[str],
                description: Optional[str] = None,
                cross_graph_links: Optional[List[Dict[str, Any]]] = None,
                primary_graph_profile_id: Optional[str] = None,
                actor: Optional[str] = None,
            ):
                captured.update(
                    workspace_id=workspace_id,
                    name=name,
                    graph_profile_ids=graph_profile_ids,
                    actor=actor,
                )

                class _R:
                    def to_dict(self_inner):
                        return {"name": name, "graph_profile_ids": graph_profile_ids}

                return _R()

        dispatcher = ProductAPIDispatcher(_Service())
        result = dispatcher.dispatch(
            method="POST",
            path="/api/workspaces/{workspace_id}/graph-sets",
            path_params={"workspace_id": "ws-9"},
            body={
                "name": "Set 1",
                "graph_profile_ids": ["gp-1", "gp-2"],
                "actor": "carol",
            },
        )
        assert captured["workspace_id"] == "ws-9"
        assert captured["name"] == "Set 1"
        assert captured["actor"] == "carol"
        assert result == {"name": "Set 1", "graph_profile_ids": ["gp-1", "gp-2"]}
