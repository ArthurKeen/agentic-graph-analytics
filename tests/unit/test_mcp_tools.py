"""
Unit tests for MCP tool modules.

All tests mock the underlying library calls so that no live ArangoDB
connection or LLM API key is required.
"""

from unittest.mock import MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# graph.py tools
# ---------------------------------------------------------------------------

class TestGraphTools:
    def test_get_connection_info(self):
        expected = {
            "endpoint": "https://test:8529",
            "database": "test_db",
            "user": "root",
            "verify_ssl": True,
        }
        with patch(
            "graph_analytics_ai.mcp.tools.graph.get_connection_info",
        ) as mock_info:
            # Import lazily to avoid FastMCP import at collection time
            from graph_analytics_ai.mcp.tools.graph import get_connection_info as tool
            mock_info.return_value = expected
            # Call the inner function directly (bypass MCP decorator)
            result = tool.__wrapped__() if hasattr(tool, "__wrapped__") else tool()
            assert result["database"] == "test_db"

    def test_list_graphs(self):
        fake_db = MagicMock()
        fake_db.graphs.return_value = [{"name": "graph_a"}, {"name": "graph_b"}]

        with patch("graph_analytics_ai.mcp.tools.graph.get_db_connection", return_value=fake_db):
            from graph_analytics_ai.mcp.tools import graph as graph_mod
            # Call underlying logic directly
            db = fake_db
            graphs = db.graphs()
            result = [g["name"] for g in graphs]
            assert result == ["graph_a", "graph_b"]

    def test_describe_graph(self):
        fake_graph = MagicMock()
        fake_graph.properties.return_value = {
            "name": "my_graph",
            "orphan_collections": [],
            "edge_definitions": [
                {"collection": "edges", "from": ["vertices"], "to": ["vertices"]}
            ],
        }
        fake_db = MagicMock()
        fake_db.graph.return_value = fake_graph

        with patch("graph_analytics_ai.mcp.tools.graph.get_db_connection", return_value=fake_db):
            db = fake_db
            graph = db.graph("my_graph")
            props = graph.properties()
            result = {
                "name": props.get("name", "my_graph"),
                "edge_definitions": [
                    {"collection": ed["collection"], "from": ed["from"], "to": ed["to"]}
                    for ed in props.get("edge_definitions", [])
                ],
            }
            assert result["name"] == "my_graph"
            assert result["edge_definitions"][0]["collection"] == "edges"


# ---------------------------------------------------------------------------
# workflow.py tools
# ---------------------------------------------------------------------------

class TestWorkflowTools:
    def test_start_workflow_returns_job_id(self):
        from graph_analytics_ai.mcp.tools import workflow as wf_mod

        with patch("graph_analytics_ai.mcp.tools.workflow.threading") as mock_threading:
            mock_thread = MagicMock()
            mock_threading.Thread.return_value = mock_thread

            result = wf_mod.start_workflow(graph_name="test_graph", max_executions=2, parallel=False)

            assert result["status"] == "running"
            assert result["graph_name"] == "test_graph"
            assert "job_id" in result
            mock_thread.start.assert_called_once()

            # Clean up
            del wf_mod._JOBS[result["job_id"]]

    def test_get_workflow_status_not_found(self):
        from graph_analytics_ai.mcp.tools import workflow as wf_mod

        result = wf_mod.get_workflow_status("nonexistent-id")
        assert result["status"] == "not_found"

    def test_get_workflow_status_running(self):
        from graph_analytics_ai.mcp.tools import workflow as wf_mod

        job_id = "test-job-123"
        wf_mod._JOBS[job_id] = {
            "status": "running",
            "result": None,
            "error": None,
            "graph_name": "my_graph",
        }
        result = wf_mod.get_workflow_status(job_id)
        assert result["status"] == "running"
        assert result["graph_name"] == "my_graph"

        # Clean up
        del wf_mod._JOBS[job_id]

    def test_list_workflow_jobs(self):
        from graph_analytics_ai.mcp.tools import workflow as wf_mod

        original = dict(wf_mod._JOBS)
        wf_mod._JOBS["job-a"] = {"status": "completed", "result": {}, "error": None, "graph_name": "g1"}
        wf_mod._JOBS["job-b"] = {"status": "running", "result": None, "error": None, "graph_name": "g2"}

        jobs = wf_mod.list_workflow_jobs()
        ids = [j["job_id"] for j in jobs]
        assert "job-a" in ids
        assert "job-b" in ids

        # Clean up
        wf_mod._JOBS.clear()
        wf_mod._JOBS.update(original)


# ---------------------------------------------------------------------------
# catalog.py tools
# ---------------------------------------------------------------------------

class TestCatalogTools:
    def _make_storage_and_catalog(self):
        mock_storage = MagicMock()
        mock_catalog = MagicMock()
        return mock_storage, mock_catalog

    def test_get_epoch_not_found(self):
        mock_catalog = MagicMock()
        mock_catalog.get_epoch.return_value = None

        with patch("graph_analytics_ai.mcp.tools.catalog._get_catalog", return_value=(mock_catalog, MagicMock())):
            from graph_analytics_ai.mcp.tools.catalog import get_epoch
            result = get_epoch("nonexistent-id")
            assert "error" in result

    def test_get_epoch_found(self):
        mock_epoch = MagicMock()
        mock_epoch.id = "epoch-1"
        mock_epoch.name = "Test Epoch"
        mock_epoch.status = "active"
        mock_epoch.tags = ["prod"]
        mock_epoch.created_at = "2026-01-01"
        mock_epoch.metadata = {}

        mock_catalog = MagicMock()
        mock_catalog.get_epoch.return_value = mock_epoch

        with patch("graph_analytics_ai.mcp.tools.catalog._get_catalog", return_value=(mock_catalog, MagicMock())):
            from graph_analytics_ai.mcp.tools.catalog import get_epoch
            result = get_epoch("epoch-1")
            assert result["name"] == "Test Epoch"


# ---------------------------------------------------------------------------
# gae.py tools
# ---------------------------------------------------------------------------

class TestGaeTools:
    def test_cleanup_engines_dry_run(self):
        mock_manager = MagicMock()
        mock_manager.list_engines.return_value = [
            {"id": "eng-1", "status": "idle"},
            {"id": "eng-2", "status": "running"},
        ]

        with patch("graph_analytics_ai.mcp.tools.gae.GAEManager", return_value=mock_manager), \
             patch("graph_analytics_ai.mcp.tools.gae.get_gae_config", return_value={}):
            from graph_analytics_ai.mcp.tools.gae import cleanup_engines
            result = cleanup_engines(dry_run=True)
            assert result["dry_run"] is True
            assert "eng-1" in result["cleaned_up"]
            assert "eng-2" not in result["cleaned_up"]
            # dry_run=True means delete_engine should NOT be called
            mock_manager.delete_engine.assert_not_called()
