"""Tests for new GAE connection methods added for gap resolution."""

import pytest
from unittest.mock import patch, MagicMock, Mock

from graph_analytics_ai.gae_connection import GenAIGAEConnection


class TestGenAIGAEConnectionNewMethods:
    """Tests for new methods added to GenAIGAEConnection."""

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_list_services(self, mock_get_config, mock_env_self_managed):
        """Test list_services() method."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()

        # Mock JWT token
        gae.jwt_token = "test-token"

        # Mock requests.post
        with patch("graph_analytics_ai.gae_connection.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "services": [
                    {"serviceId": "arangodb-gral-abc123", "status": "running"},
                    {"serviceId": "arangodb-gral-def456", "status": "running"},
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            services = gae.list_services()

            assert len(services) == 2
            assert services[0]["serviceId"] == "arangodb-gral-abc123"
            mock_post.assert_called_once()

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_list_services_empty(self, mock_get_config, mock_env_self_managed):
        """Test list_services() with no services."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.jwt_token = "test-token"

        with patch("graph_analytics_ai.gae_connection.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"services": []}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            services = gae.list_services()
            assert services == []

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_list_graphs(self, mock_get_config, mock_env_self_managed):
        """Test list_graphs() method."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = "arangodb-gral-abc123"
        gae.jwt_token = "test-token"

        with patch.object(gae, "_make_request") as mock_request:
            mock_request.return_value = [
                {"graph_id": "1", "vertex_count": 100},
                {"graph_id": "2", "vertex_count": 200},
            ]

            graphs = gae.list_graphs()

            assert len(graphs) == 2
            assert graphs[0]["graph_id"] == "1"
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="v1/graphs",
                error_message="Failed to list graphs",
            )

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_list_graphs_no_engine(self, mock_get_config, mock_env_self_managed):
        """Test list_graphs() without engine running."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = None

        with pytest.raises(ValueError, match="No engine running"):
            gae.list_graphs()

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_delete_graph(self, mock_get_config, mock_env_self_managed):
        """Test delete_graph() method."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = "arangodb-gral-abc123"
        gae.jwt_token = "test-token"

        with patch.object(gae, "_make_request") as mock_request:
            mock_request.return_value = {"status": "deleted"}

            result = gae.delete_graph("1")

            assert result["status"] == "deleted"
            mock_request.assert_called_once_with(
                method="DELETE",
                endpoint="v1/graphs/1",
                success_message="Graph 1 deleted successfully",
                error_message="Failed to delete graph 1",
            )

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_delete_graph_no_engine(self, mock_get_config, mock_env_self_managed):
        """Test delete_graph() without engine running."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = None

        with pytest.raises(ValueError, match="No engine running"):
            gae.delete_graph("1")

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_wait_for_job_completed(self, mock_get_config, mock_env_self_managed):
        """Test wait_for_job() with completed job."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = "arangodb-gral-abc123"

        with patch.object(gae, "get_job") as mock_get_job:
            mock_get_job.return_value = {
                "job_id": "job1",
                "state": "completed",
                "status": {"state": "completed"},
            }

            result = gae.wait_for_job("job1", poll_interval=0.1, max_wait=5)

            assert result["state"] == "completed"
            assert mock_get_job.called

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_wait_for_job_failed(self, mock_get_config, mock_env_self_managed):
        """Test wait_for_job() with failed job."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = "arangodb-gral-abc123"

        with patch.object(gae, "get_job") as mock_get_job:
            mock_get_job.return_value = {
                "job_id": "job1",
                "state": "failed",
                "status": {"state": "failed", "error": "Test error"},
            }

            with pytest.raises(RuntimeError, match="Job job1 failed"):
                gae.wait_for_job("job1", poll_interval=0.1, max_wait=5)

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_wait_for_job_timeout(self, mock_get_config, mock_env_self_managed):
        """Test wait_for_job() timeout."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = "arangodb-gral-abc123"

        with patch.object(gae, "get_job") as mock_get_job:
            mock_get_job.return_value = {
                "job_id": "job1",
                "state": "running",
                "status": {"state": "running"},
            }

            with patch("time.time", side_effect=[0, 0, 10]):  # Elapsed time > max_wait
                with pytest.raises(TimeoutError, match="did not complete within"):
                    gae.wait_for_job("job1", poll_interval=0.1, max_wait=5)

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_list_jobs(self, mock_get_config, mock_env_self_managed):
        """Test list_jobs() method."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = "arangodb-gral-abc123"
        gae.jwt_token = "test-token"

        with patch.object(gae, "_make_request") as mock_request:
            mock_request.return_value = [
                {"job_id": "job1", "state": "completed"},
                {"job_id": "job2", "state": "running"},
            ]

            jobs = gae.list_jobs()

            assert len(jobs) == 2
            assert jobs[0]["job_id"] == "job1"
            mock_request.assert_called_once_with(
                method="GET", endpoint="v1/jobs", error_message="Failed to list jobs"
            )

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_list_jobs_no_engine(self, mock_get_config, mock_env_self_managed):
        """Test list_jobs() without engine running."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = None

        with pytest.raises(ValueError, match="No engine running"):
            gae.list_jobs()

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_test_connection_success(self, mock_get_config, mock_env_self_managed):
        """Test test_connection() with successful connection."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()

        with patch.object(gae, "_get_jwt_token"), patch.object(
            gae, "list_services", return_value=[]
        ):

            result = gae.test_connection()

            assert result is True

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_test_connection_failure(self, mock_get_config, mock_env_self_managed):
        """Test test_connection() with failed connection."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()

        with patch.object(
            gae, "_get_jwt_token", side_effect=Exception("Connection failed")
        ):
            result = gae.test_connection()

            assert result is False

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_load_graph_with_graph_name(self, mock_get_config, mock_env_self_managed):
        """Test load_graph() with graph_name parameter."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = "arangodb-gral-abc123"
        gae.db_name = "testdb"
        gae.jwt_token = "test-token"

        with patch.object(gae, "_make_request") as mock_request:
            mock_request.return_value = {"job_id": "job1", "graph_id": "graph1"}

            result = gae.load_graph(graph_name="test_graph")

            assert result["job_id"] == "job1"
            assert result["graph_id"] == "graph1"
            assert result["id"] == "job1"  # Normalized

            # Verify payload includes graph_name
            call_args = mock_request.call_args
            assert call_args[1]["payload"]["graph_name"] == "test_graph"
            assert call_args[1]["payload"]["database"] == "testdb"

    @patch("graph_analytics_ai.gae_connection.get_arango_config")
    def test_store_results_optional_database(
        self, mock_get_config, mock_env_self_managed
    ):
        """Test store_results() with optional database parameter."""
        mock_config = {
            "endpoint": "https://test.com:8529",
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }
        mock_get_config.return_value = mock_config

        gae = GenAIGAEConnection()
        gae.engine_id = "arangodb-gral-abc123"
        gae.db_name = "testdb"
        gae.jwt_token = "test-token"

        with patch.object(gae, "_make_request") as mock_request:
            mock_request.return_value = {"job_id": "store_job1", "graph_id": "graph1"}

            # Test without database (should use self.db_name)
            result = gae.store_results(
                target_collection="persons",
                job_ids=["job1"],
                attribute_names=["pagerank_score"],
            )

            assert result["job_id"] == "store_job1"

            # Verify payload uses self.db_name
            call_args = mock_request.call_args
            assert call_args[1]["payload"]["database"] == "testdb"

            # Test with explicit database
            gae.store_results(
                target_collection="persons",
                job_ids=["job1"],
                attribute_names=["pagerank_score"],
                database="otherdb",
            )

            call_args2 = mock_request.call_args
            assert call_args2[1]["payload"]["database"] == "otherdb"
