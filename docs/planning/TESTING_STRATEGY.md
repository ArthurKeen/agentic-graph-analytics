# Comprehensive Testing Strategy

**Version:** 1.0  
**Date:** December 2025  
**Status:** Planning Phase  

---

## Executive Summary

This document outlines the comprehensive testing strategy for the Graph Analytics AI platform, covering all three major features: Agentic AI Workflow, Web UI, and Natural Language Query.

### Testing Principles

1. **Test-Driven Development (TDD)** - Write tests before code when possible
2. **High Coverage** - Target 90%+ code coverage
3. **Fast Feedback** - Unit tests run in <5 seconds, full suite in <2 minutes
4. **Isolated Tests** - Each test is independent and deterministic
5. **Realistic Mocks** - Mocks reflect real-world behavior
6. **CI/CD Integration** - All tests run automatically on every commit

---

## 1. Testing Pyramid

```
                    ▲
                   /E\      E2E Tests (5%)
                  /───\     - Full workflows
                 /  I  \    - Real systems
                /───────\   
               /    I    \  Integration Tests (25%)
              /───────────\ - Component integration
             /      U      \- API contracts
            /───────────────\
           /        U        \ Unit Tests (70%)
          /──────────────────\- Individual functions
         /          U         \- Pure logic
        /────────────────────────\
```

**Distribution:**
- **70% Unit Tests** - Fast, isolated, comprehensive
- **25% Integration Tests** - Component interactions
- **5% E2E Tests** - Full system workflows

---

## 2. Unit Testing Strategy

### 2.1 What to Unit Test

**Core Library (Existing):**
- ✅ All public APIs
- ✅ Configuration management
- ✅ Database connections
- ✅ GAE orchestration logic
- ✅ Result management
- ✅ Query helpers
- ✅ Export utilities
- ✅ Error handling
- ✅ Cost calculations

**New AI Features:**
- Document processing
- PRD generation
- Use case generation
- Template generation
- Report generation
- LLM response parsing
- Schema analysis
- Query understanding (NLQ)
- AQL generation
- Result interpretation

### 2.2 Unit Testing Framework

**Python (Core Library + AI Features):**
```python
# Testing stack
pytest==7.4.0           # Test runner
pytest-cov==4.1.0       # Coverage reporting
pytest-mock==3.11.1     # Mocking utilities
pytest-asyncio==0.21.0  # Async test support
freezegun==1.2.2        # Time mocking
faker==19.3.1           # Fake data generation
responses==0.23.1       # HTTP mocking
```

**JavaScript/TypeScript (Web UI):**
```json
{
  "devDependencies": {
    "vitest": "^1.0.0",           // Test runner
    "@testing-library/react": "^14.0.0",  // React testing
    "@testing-library/jest-dom": "^6.1.0", // DOM matchers
    "msw": "^2.0.0",              // API mocking
    "playwright": "^1.40.0"       // E2E testing
  }
}
```

### 2.3 Unit Test Examples

#### Example 1: Testing Configuration Loading

```python
# tests/test_config.py
import pytest
from graph_analytics_ai.config import get_arango_config, ArangoConfig
from graph_analytics_ai.config import ConfigurationError

class TestArangoConfig:
    """Test ArangoDB configuration loading."""
    
    def test_get_config_from_env(self, monkeypatch):
        """Test loading config from environment variables."""
        # Arrange
        monkeypatch.setenv("ARANGO_ENDPOINT", "https://test.db:8529")
        monkeypatch.setenv("ARANGO_USER", "testuser")
        monkeypatch.setenv("ARANGO_PASSWORD", "testpass")
        monkeypatch.setenv("ARANGO_DATABASE", "testdb")
        
        # Act
        config = get_arango_config()
        
        # Assert
        assert config.endpoint == "https://test.db:8529"
        assert config.user == "testuser"
        assert config.password == "testpass"
        assert config.database == "testdb"
    
    def test_missing_required_field_raises_error(self, monkeypatch):
        """Test that missing required fields raise ConfigurationError."""
        # Arrange
        monkeypatch.setenv("ARANGO_ENDPOINT", "https://test.db:8529")
        # Missing user, password, database
        
        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            get_arango_config()
        
        assert "ARANGO_USER" in str(exc_info.value)
    
    def test_config_validation(self):
        """Test configuration validation logic."""
        # Act & Assert
        with pytest.raises(ConfigurationError):
            ArangoConfig(
                endpoint="invalid-url",  # Invalid URL
                user="user",
                password="pass",
                database="db"
            )
```

#### Example 2: Testing LLM Provider with Mocks

```python
# tests/ai/llm/test_openrouter.py
import pytest
import responses
from graph_analytics_ai.ai.llm import OpenRouterProvider

class TestOpenRouterProvider:
    """Test OpenRouter LLM provider."""
    
    @pytest.fixture
    def provider(self):
        """Create test provider instance."""
        return OpenRouterProvider(
            api_key="test-key",
            model="google/gemini-2.5-flash"
        )
    
    @responses.activate
    def test_generate_success(self, provider):
        """Test successful text generation."""
        # Arrange
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [{
                    "message": {
                        "content": "Generated text response"
                    }
                }],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            },
            status=200
        )
        
        # Act
        result = provider.generate("Test prompt")
        
        # Assert
        assert result == "Generated text response"
        assert len(responses.calls) == 1
        assert responses.calls[0].request.headers["Authorization"] == "Bearer test-key"
    
    @responses.activate
    def test_generate_api_error(self, provider):
        """Test handling of API errors."""
        # Arrange
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={"error": "API key invalid"},
            status=401
        )
        
        # Act & Assert
        with pytest.raises(LLMProviderError) as exc_info:
            provider.generate("Test prompt")
        
        assert "401" in str(exc_info.value)
        assert "API key invalid" in str(exc_info.value)
    
    def test_rate_limiting(self, provider, mocker):
        """Test rate limiting behavior."""
        # Arrange
        mock_sleep = mocker.patch("time.sleep")
        mock_request = mocker.patch.object(
            provider, "_make_request",
            side_effect=[
                RateLimitError("Rate limited"),
                RateLimitError("Rate limited"),
                {"choices": [{"message": {"content": "Success"}}]}
            ]
        )
        
        # Act
        result = provider.generate("Test prompt")
        
        # Assert
        assert result == "Success"
        assert mock_request.call_count == 3
        assert mock_sleep.call_count == 2  # Slept twice for retries
```

#### Example 3: Testing Schema Analysis

```python
# tests/ai/schema/test_analyzer.py
import pytest
from graph_analytics_ai.ai.schema import SchemaAnalyzer, GraphSchema

class TestSchemaAnalyzer:
    """Test graph schema analysis."""
    
    @pytest.fixture
    def mock_db(self, mocker):
        """Create mock database connection."""
        mock = mocker.Mock()
        mock.collections.return_value = [
            {"name": "customers", "type": "document"},
            {"name": "products", "type": "document"},
            {"name": "purchases", "type": "edge"}
        ]
        return mock
    
    def test_analyze_basic_schema(self, mock_db):
        """Test basic schema analysis."""
        # Arrange
        analyzer = SchemaAnalyzer(mock_db)
        
        # Act
        schema = analyzer.analyze()
        
        # Assert
        assert len(schema.vertex_collections) == 2
        assert "customers" in schema.vertex_collections
        assert "products" in schema.vertex_collections
        assert len(schema.edge_collections) == 1
        assert "purchases" in schema.edge_collections
    
    def test_analyze_with_samples(self, mock_db, mocker):
        """Test schema analysis with document samples."""
        # Arrange
        mock_db.collection.return_value.all.return_value = [
            {"_key": "1", "name": "John", "email": "john@example.com"},
            {"_key": "2", "name": "Jane", "email": "jane@example.com"}
        ]
        analyzer = SchemaAnalyzer(mock_db)
        
        # Act
        schema = analyzer.analyze(sample_size=10)
        
        # Assert
        customer_schema = schema.vertex_collections["customers"]
        assert "name" in customer_schema.attributes
        assert "email" in customer_schema.attributes
        assert customer_schema.sample_count == 2
```

#### Example 4: Testing NLQ Query Understanding

```python
# tests/nlq/test_query_understanding.py
import pytest
from graph_analytics_ai.nlq import QueryUnderstanding, QueryIntent

class TestQueryUnderstanding:
    """Test natural language query understanding."""
    
    @pytest.fixture
    def understanding(self, mocker):
        """Create query understanding instance with mocked LLM."""
        mock_llm = mocker.Mock()
        return QueryUnderstanding(llm_provider=mock_llm)
    
    def test_parse_simple_filter_query(self, understanding, mocker):
        """Test parsing simple filter query."""
        # Arrange
        query = "Show me customers in California"
        schema = GraphSchema(
            vertex_collections={"customers": {"state": "string"}},
            edge_collections={}
        )
        
        mocker.patch.object(
            understanding.llm,
            "generate_structured",
            return_value={
                "query_type": "simple_query",
                "entities": ["customers"],
                "attributes": ["state"],
                "operations": ["filter"],
                "values": {"state": "California"},
                "confidence": "high"
            }
        )
        
        # Act
        intent = understanding.parse_query(query, schema)
        
        # Assert
        assert intent.query_type == "simple_query"
        assert "customers" in intent.entities
        assert intent.values["state"] == "California"
        assert intent.confidence == "high"
    
    def test_parse_analytics_query(self, understanding, mocker):
        """Test parsing query requiring graph analytics."""
        # Arrange
        query = "Who are the most influential customers?"
        schema = GraphSchema(
            vertex_collections={"customers": {}},
            edge_collections={"follows": {}}
        )
        
        mocker.patch.object(
            understanding.llm,
            "generate_structured",
            return_value={
                "query_type": "analytics",
                "entities": ["customers"],
                "algorithm": "pagerank",
                "confidence": "high"
            }
        )
        
        # Act
        intent = understanding.parse_query(query, schema)
        
        # Assert
        assert intent.query_type == "analytics"
        assert intent.algorithm == "pagerank"
```

### 2.4 Test Coverage Requirements

**Minimum Coverage Targets:**
- Core library: 90%
- AI features: 85%
- Web UI (logic): 80%
- CLI tools: 75%

**Coverage Reports:**
```bash
# Python coverage
pytest --cov=graph_analytics_ai --cov-report=html --cov-report=term

# JavaScript coverage
npm run test:coverage
```

**Coverage Metrics:**
- Line coverage
- Branch coverage
- Function coverage

---

## 3. Integration Testing Strategy

### 3.1 What to Integration Test

**Component Integration:**
- LLM provider → Schema analyzer
- Schema analyzer → PRD generator
- PRD generator → Use case generator
- Use case generator → Template generator
- Template generator → GAE orchestrator
- GAE orchestrator → Result manager
- Result manager → Report generator

**API Integration:**
- REST API → Core library
- WebSocket → Progress updates
- NLQ engine → AQL executor
- Web UI → Backend API

**Database Integration:**
- ArangoDB connections
- GAE engine lifecycle
- Query execution
- Result storage

### 3.2 Integration Test Examples

#### Example 1: End-to-End AI Workflow

```python
# tests/integration/test_ai_workflow.py
import pytest
from graph_analytics_ai.ai import AIWorkflowOrchestrator

@pytest.mark.integration
class TestAIWorkflowIntegration:
    """Integration tests for complete AI workflow."""
    
    @pytest.fixture
    def test_db(self):
        """Set up test database with sample data."""
        # Create test database
        # Populate with sample collections
        # Return connection
        pass
    
    @pytest.fixture
    def workflow(self, test_db):
        """Create workflow orchestrator with test LLM."""
        return AIWorkflowOrchestrator(
            llm_provider="openrouter",
            llm_api_key=os.getenv("TEST_OPENROUTER_KEY"),
            database=test_db
        )
    
    def test_complete_workflow_execution(self, workflow, tmp_path):
        """Test complete workflow from requirements to report."""
        # Arrange
        requirements_file = tmp_path / "requirements.md"
        requirements_file.write_text("""
        # Test Requirements
        Analyze customer purchase patterns to identify high-value customers.
        """)
        
        workflow.add_document(requirements_file, doc_type="requirements")
        
        # Act
        result = workflow.run_complete_workflow(
            database_name="test_db",
            output_dir=str(tmp_path)
        )
        
        # Assert
        assert result.status == "success"
        assert result.prd is not None
        assert len(result.use_cases) > 0
        assert len(result.analyses) > 0
        assert result.report is not None
        
        # Verify files created
        assert (tmp_path / "prd.md").exists()
        assert (tmp_path / "report.md").exists()
    
    def test_workflow_with_invalid_schema(self, workflow):
        """Test workflow handles invalid schema gracefully."""
        # Act & Assert
        with pytest.raises(WorkflowError) as exc_info:
            workflow.run_complete_workflow(
                database_name="nonexistent_db"
            )
        
        assert "database not found" in str(exc_info.value).lower()
```

#### Example 2: API Integration

```python
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for REST API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_nlq_query_endpoint(self, client):
        """Test natural language query endpoint."""
        # Act
        response = client.post(
            "/api/v1/nlq/query",
            json={"query": "Show me high-risk customers"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "explanation" in data
        assert "generated_aql" in data
    
    def test_workflow_execution_endpoint(self, client, tmp_path):
        """Test workflow execution endpoint."""
        # Arrange - Upload document
        files = {
            "file": ("requirements.md", "# Test requirements", "text/markdown")
        }
        upload_response = client.post("/api/v1/documents", files=files)
        doc_id = upload_response.json()["id"]
        
        # Act - Start workflow
        workflow_response = client.post(
            "/api/v1/workflows",
            json={
                "name": "test_workflow",
                "document_ids": [doc_id],
                "database_name": "test_db"
            }
        )
        
        # Assert
        assert workflow_response.status_code == 201
        workflow_id = workflow_response.json()["workflow_id"]
        
        # Wait for completion (with timeout)
        # Check status endpoint
        # Verify results
```

#### Example 3: Database Integration

```python
# tests/integration/test_database.py
import pytest
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

@pytest.mark.integration
@pytest.mark.requires_db
class TestDatabaseIntegration:
    """Integration tests with real database."""
    
    @pytest.fixture(scope="class")
    def db_connection(self):
        """Create test database connection."""
        # Set up test database
        # Return connection
        pass
    
    def test_gae_analysis_execution(self, db_connection):
        """Test real GAE analysis execution."""
        # Arrange
        config = AnalysisConfig(
            name="test_pagerank",
            vertex_collections=["test_vertices"],
            edge_collections=["test_edges"],
            algorithm="pagerank"
        )
        orchestrator = GAEOrchestrator()
        
        # Act
        result = orchestrator.run_analysis(config)
        
        # Assert
        assert result.status == "success"
        assert result.documents_updated > 0
        assert result.estimated_cost_usd > 0
    
    def test_result_storage_and_retrieval(self, db_connection):
        """Test storing and retrieving analysis results."""
        # Arrange
        # Run analysis
        # Store results
        
        # Act
        # Retrieve results
        
        # Assert
        # Verify results match
        pass
```

### 3.3 Integration Test Configuration

**Test Database Setup:**
```python
# tests/conftest.py
import pytest
from arango import ArangoClient

@pytest.fixture(scope="session")
def test_db():
    """Set up test database for integration tests."""
    client = ArangoClient(hosts=os.getenv("TEST_ARANGO_ENDPOINT"))
    sys_db = client.db(
        "_system",
        username=os.getenv("TEST_ARANGO_USER"),
        password=os.getenv("TEST_ARANGO_PASSWORD")
    )
    
    # Create test database
    if not sys_db.has_database("test_db"):
        sys_db.create_database("test_db")
    
    db = client.db("test_db", ...)
    
    # Populate with test data
    _populate_test_data(db)
    
    yield db
    
    # Cleanup
    sys_db.delete_database("test_db")

def _populate_test_data(db):
    """Populate database with test data."""
    # Create collections
    # Insert test documents
    pass
```

---

## 4. Mock Testing Strategy

### 4.1 What to Mock

**External Services:**
- LLM APIs (OpenRouter, OpenAI, Anthropic)
- ArangoDB connections (in unit tests)
- GAE engine API
- File system operations
- Network requests
- Time-dependent operations

**Why Mock:**
- Speed (tests run in milliseconds)
- Reliability (no external dependencies)
- Cost (no API charges)
- Determinism (same results every time)
- Isolation (test one thing at a time)

### 4.2 Mock Strategies

#### Strategy 1: pytest-mock (Python)

```python
# tests/test_with_mocks.py
import pytest

def test_llm_call_with_mock(mocker):
    """Test function that calls LLM without actually calling it."""
    # Arrange
    mock_llm = mocker.Mock()
    mock_llm.generate.return_value = "Mocked response"
    
    # Act
    result = some_function_that_uses_llm(mock_llm)
    
    # Assert
    assert result == "Expected result based on mocked response"
    mock_llm.generate.assert_called_once_with("Expected prompt")
```

#### Strategy 2: responses (HTTP Mocking)

```python
# tests/test_http_mock.py
import responses
import requests

@responses.activate
def test_api_call():
    """Test HTTP API call with mocked response."""
    # Arrange
    responses.add(
        responses.POST,
        "https://api.example.com/endpoint",
        json={"status": "success"},
        status=200
    )
    
    # Act
    response = requests.post("https://api.example.com/endpoint")
    
    # Assert
    assert response.json()["status"] == "success"
```

#### Strategy 3: monkeypatch (Environment)

```python
# tests/test_config_mock.py
def test_config_with_env_mock(monkeypatch):
    """Test configuration with mocked environment variables."""
    # Arrange
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("API_ENDPOINT", "https://test.api")
    
    # Act
    config = load_config()
    
    # Assert
    assert config.api_key == "test-key"
```

#### Strategy 4: MSW (Mock Service Worker) for Web UI

```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.post('/api/v1/nlq/query', () => {
    return HttpResponse.json({
      results: [{ id: 1, name: 'Test' }],
      explanation: 'Found 1 result'
    })
  }),
  
  http.get('/api/v1/workflows/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: 'completed',
      progress: 100
    })
  })
]
```

### 4.3 Mock Best Practices

**DO:**
- ✅ Mock external services (APIs, databases in unit tests)
- ✅ Mock time-dependent operations (dates, delays)
- ✅ Mock random operations (for deterministic tests)
- ✅ Mock file system in unit tests
- ✅ Verify mock calls (assert_called_with, etc.)
- ✅ Reset mocks between tests

**DON'T:**
- ❌ Mock internal functions (test real implementation)
- ❌ Over-mock (mocking everything defeats the purpose)
- ❌ Mock in integration tests (use real services)
- ❌ Hardcode mock responses (use realistic data)
- ❌ Forget to clean up mocks

### 4.4 Realistic Mock Data

```python
# tests/fixtures/mock_data.py
"""Realistic mock data for tests."""

MOCK_SCHEMA = {
    "vertex_collections": {
        "customers": {
            "attributes": ["name", "email", "created_at", "risk_score"],
            "sample_count": 1000
        },
        "products": {
            "attributes": ["name", "category", "price"],
            "sample_count": 500
        }
    },
    "edge_collections": {
        "purchases": {
            "attributes": ["quantity", "date", "amount"],
            "from": "customers",
            "to": "products",
            "sample_count": 5000
        }
    }
}

MOCK_LLM_RESPONSES = {
    "schema_analysis": """
    Based on the schema, this is a customer-product purchase network.
    Suitable algorithms: PageRank (customer influence), 
    WCC (customer segments), Label Propagation (product communities).
    """,
    
    "prd_generation": """
    # Product Requirements Document
    ## Objective
    Analyze customer purchase patterns...
    """,
    
    "use_case_generation": [
        {
            "name": "Customer Influence Analysis",
            "algorithm": "pagerank",
            "business_value": "Identify top customers for loyalty programs"
        }
    ]
}

def get_mock_analysis_result():
    """Get realistic mock analysis result."""
    return {
        "status": "success",
        "vertex_count": 1000,
        "edge_count": 5000,
        "documents_updated": 1000,
        "duration_seconds": 125.5,
        "estimated_cost_usd": 0.15
    }
```

---

## 5. Test Organization

### 5.1 Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── fixtures/                   # Test data and mocks
│   ├── mock_data.py
│   ├── sample_documents/
│   └── test_schemas/
│
├── unit/                       # Unit tests (70%)
│   ├── test_config.py
│   ├── test_db_connection.py
│   ├── test_gae_orchestrator.py
│   ├── ai/
│   │   ├── llm/
│   │   │   ├── test_openrouter.py
│   │   │   ├── test_openai.py
│   │   │   └── test_factory.py
│   │   ├── schema/
│   │   │   └── test_analyzer.py
│   │   └── generation/
│   │       ├── test_prd.py
│   │       ├── test_use_cases.py
│   │       └── test_templates.py
│   └── nlq/
│       ├── test_query_understanding.py
│       ├── test_aql_generator.py
│       └── test_result_interpreter.py
│
├── integration/                # Integration tests (25%)
│   ├── test_ai_workflow.py
│   ├── test_api.py
│   ├── test_database.py
│   └── test_nlq_pipeline.py
│
├── e2e/                        # End-to-end tests (5%)
│   ├── test_complete_workflow.py
│   ├── test_ui_workflows.py
│   └── test_api_workflows.py
│
└── performance/                # Performance tests
    ├── test_large_graphs.py
    └── test_query_performance.py
```

### 5.2 Test Naming Conventions

**Format:** `test_<what>_<condition>_<expected_result>`

**Examples:**
```python
# Good
def test_get_config_with_valid_env_returns_config():
    pass

def test_parse_query_with_invalid_syntax_raises_error():
    pass

def test_generate_aql_for_simple_filter_returns_valid_query():
    pass

# Bad
def test_config():  # Too vague
    pass

def test_1():  # Meaningless
    pass

def test_everything():  # Too broad
    pass
```

### 5.3 Test Markers

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (slower, requires services)",
    "e2e: End-to-end tests (slowest, full system)",
    "slow: Tests that take >1 second",
    "requires_db: Tests that require database",
    "requires_llm: Tests that require LLM API",
    "smoke: Critical path smoke tests"
]
```

**Usage:**
```bash
# Run only unit tests
pytest -m unit

# Run everything except slow tests
pytest -m "not slow"

# Run smoke tests
pytest -m smoke

# Run tests that don't require external services
pytest -m "not requires_db and not requires_llm"
```

---

## 6. Testing for Backward Compatibility

### 6.1 Compatibility Test Suite

```python
# tests/compatibility/test_backward_compatibility.py
import pytest
from graph_analytics_ai import (
    GAEOrchestrator, AnalysisConfig, get_arango_config
)

@pytest.mark.compatibility
class TestBackwardCompatibility:
    """Ensure new features don't break existing functionality."""
    
    def test_existing_api_unchanged(self):
        """Test that existing APIs work exactly as before."""
        # This test validates that the exact same code
        # that worked in v1.2.0 still works now
        
        config = AnalysisConfig(
            name="test",
            vertex_collections=["vertices"],
            edge_collections=["edges"],
            algorithm="pagerank"
        )
        
        orchestrator = GAEOrchestrator()
        # Should work without any AI features
        assert orchestrator is not None
    
    def test_config_loading_unchanged(self, monkeypatch):
        """Test that configuration loading is unchanged."""
        monkeypatch.setenv("ARANGO_ENDPOINT", "https://test:8529")
        monkeypatch.setenv("ARANGO_USER", "user")
        monkeypatch.setenv("ARANGO_PASSWORD", "pass")
        monkeypatch.setenv("ARANGO_DATABASE", "db")
        
        config = get_arango_config()
        
        assert config.endpoint == "https://test:8529"
        # All existing fields still work
    
    def test_ai_features_optional(self):
        """Test that AI features are truly optional."""
        # Should work without AI_WORKFLOW_ENABLED
        # Should work without LLM API keys
        # Should not import AI modules unless explicitly requested
        
        import graph_analytics_ai
        
        # These should work
        assert hasattr(graph_analytics_ai, 'GAEOrchestrator')
        assert hasattr(graph_analytics_ai, 'AnalysisConfig')
        
        # AI features should not be loaded automatically
        # (unless explicitly imported)
```

### 6.2 Regression Test Suite

**Capture behavior of existing features:**

```python
# tests/regression/test_existing_features.py
import pytest

@pytest.mark.regression
class TestExistingFeatures:
    """Regression tests for existing features."""
    
    def test_pagerank_results_consistent(self):
        """Test that PageRank produces consistent results."""
        # Use fixed test data
        # Run PageRank
        # Compare against known good results
        pass
    
    def test_cost_calculation_unchanged(self):
        """Test that cost calculations haven't changed."""
        # For a known analysis
        # Cost should be exactly the same as v1.2.0
        pass
```

---

## 7. CI/CD Integration

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev,test]"
    
    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov=graph_analytics_ai \
          --cov-report=xml --cov-report=term
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
  
  integration-tests:
    runs-on: ubuntu-latest
    services:
      arangodb:
        image: arangodb:latest
        env:
          ARANGO_ROOT_PASSWORD: test
        ports:
          - 8529:8529
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.10"
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev,test]"
    
    - name: Run integration tests
      env:
        TEST_ARANGO_ENDPOINT: http://localhost:8529
        TEST_ARANGO_USER: root
        TEST_ARANGO_PASSWORD: test
      run: |
        pytest tests/integration -v -m integration
  
  compatibility-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run backward compatibility tests
      run: |
        pytest tests/compatibility -v -m compatibility
  
  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run linting
      run: |
        pip install ruff mypy
        ruff check .
        mypy graph_analytics_ai
```

### 7.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest tests/unit -v --tb=short
        language: system
        pass_filenames: false
        always_run: true
```

### 7.3 Test Execution Strategy

**On Every Commit (Pre-push):**
- ✅ Unit tests (70% of tests, <5 seconds)
- ✅ Linting
- ✅ Type checking

**On Pull Request:**
- ✅ Unit tests
- ✅ Integration tests (25% of tests, <2 minutes)
- ✅ Compatibility tests
- ✅ Coverage report (must maintain 90%+)

**Before Release:**
- ✅ All tests (unit + integration + e2e)
- ✅ Performance tests
- ✅ Security scans
- ✅ Load tests

**Nightly:**
- ✅ Extended integration tests
- ✅ Compatibility matrix (multiple Python versions)
- ✅ Performance regression tests

---

## 8. Test Data Management

### 8.1 Test Fixtures

```python
# tests/conftest.py
import pytest
from faker import Faker

@pytest.fixture
def fake():
    """Faker instance for generating test data."""
    return Faker()

@pytest.fixture
def sample_schema():
    """Sample graph schema for testing."""
    return {
        "vertex_collections": ["customers", "products"],
        "edge_collections": ["purchases"]
    }

@pytest.fixture
def sample_document(tmp_path, fake):
    """Create sample requirements document."""
    doc = tmp_path / "requirements.md"
    doc.write_text(f"""
    # Requirements
    {fake.text(max_nb_chars=500)}
    """)
    return doc

@pytest.fixture
def sample_analysis_config():
    """Sample analysis configuration."""
    return AnalysisConfig(
        name="test_analysis",
        vertex_collections=["test_vertices"],
        edge_collections=["test_edges"],
        algorithm="pagerank"
    )
```

### 8.2 Test Database Seeding

```python
# tests/fixtures/seed_data.py
"""Seed test database with realistic data."""

def seed_customer_data(db, count=1000):
    """Seed customer collection with test data."""
    from faker import Faker
    fake = Faker()
    
    customers = []
    for i in range(count):
        customers.append({
            "_key": f"customer_{i}",
            "name": fake.name(),
            "email": fake.email(),
            "risk_score": fake.random.uniform(0, 1),
            "created_at": fake.date_time_this_year().isoformat()
        })
    
    db.collection("customers").import_bulk(customers)
    return customers

def seed_graph_data(db, vertices=100, edges=500):
    """Seed graph with vertices and edges."""
    # Create vertices
    # Create edges
    # Return graph info
    pass
```

---

## 9. Performance Testing

### 9.1 Performance Test Examples

```python
# tests/performance/test_large_graphs.py
import pytest
import time

@pytest.mark.performance
class TestPerformance:
    """Performance tests for large graphs."""
    
    def test_pagerank_performance_1m_edges(self, large_test_db):
        """Test PageRank performance on 1M edge graph."""
        # Arrange
        config = AnalysisConfig(
            name="perf_test",
            vertex_collections=["vertices"],
            edge_collections=["edges"],
            algorithm="pagerank"
        )
        orchestrator = GAEOrchestrator()
        
        # Act
        start = time.time()
        result = orchestrator.run_analysis(config)
        duration = time.time() - start
        
        # Assert
        assert result.status == "success"
        assert duration < 300  # Should complete in <5 minutes
    
    def test_nlq_query_latency(self, nlq_engine):
        """Test NLQ query response time."""
        queries = [
            "Show me high-risk customers",
            "What are the top products?",
            "Find fraud patterns"
        ]
        
        latencies = []
        for query in queries:
            start = time.time()
            result = nlq_engine.query(query)
            latencies.append(time.time() - start)
        
        # Assert
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 1.0  # Average <1 second
        assert max(latencies) < 2.0  # Max <2 seconds
```

### 9.2 Load Testing

```python
# tests/performance/test_load.py
import pytest
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.load
def test_concurrent_queries(nlq_engine):
    """Test system under concurrent load."""
    def run_query(query_id):
        return nlq_engine.query(f"Show me data {query_id}")
    
    # Run 100 concurrent queries
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(run_query, i) for i in range(100)]
        results = [f.result() for f in futures]
    
    # Assert all succeeded
    assert len(results) == 100
    assert all(r.status == "success" for r in results)
```

---

## 10. Security Testing

### 10.1 Security Test Examples

```python
# tests/security/test_security.py
import pytest

@pytest.mark.security
class TestSecurity:
    """Security tests."""
    
    def test_sql_injection_prevention(self, nlq_engine):
        """Test that SQL injection attempts are prevented."""
        malicious_queries = [
            "Show me users WHERE 1=1; DROP TABLE customers;--",
            "'; DELETE FROM products; --",
            "1' OR '1'='1"
        ]
        
        for query in malicious_queries:
            # Should either sanitize or reject
            result = nlq_engine.query(query)
            # System should still be operational
            assert nlq_engine.is_operational()
    
    def test_api_key_not_logged(self, caplog):
        """Test that API keys are never logged."""
        provider = OpenRouterProvider(api_key="secret-key-123")
        
        with caplog.at_level(logging.DEBUG):
            provider.generate("test prompt")
        
        # Check logs don't contain key
        log_text = caplog.text
        assert "secret-key-123" not in log_text
        assert "secret" not in log_text.lower()
    
    def test_input_validation(self, api_client):
        """Test API input validation."""
        invalid_inputs = [
            {"query": "x" * 100000},  # Too long
            {"query": "\x00\x01\x02"},  # Binary data
            {"query": "<script>alert('xss')</script>"}  # XSS attempt
        ]
        
        for invalid in invalid_inputs:
            response = api_client.post("/api/v1/nlq/query", json=invalid)
            assert response.status_code == 400  # Bad request
```

---

## 11. Test Maintenance

### 11.1 Keeping Tests Green

**Practices:**
- Run tests before committing
- Fix failing tests immediately (don't accumulate)
- Keep tests fast (remove slow tests or mark them)
- Remove obsolete tests
- Update tests when requirements change

### 11.2 Test Code Quality

**Apply same standards as production code:**
- Clear naming
- DRY (Don't Repeat Yourself)
- Comments where needed
- Proper abstractions
- Maintainable

### 11.3 Test Documentation

```python
def test_complex_scenario():
    """
    Test complex workflow scenario.
    
    This test validates that when a user provides ambiguous requirements,
    the system:
    1. Detects the ambiguity
    2. Requests clarification
    3. Proceeds correctly after clarification
    
    Regression: Fixed bug #123 where ambiguous queries would fail silently.
    """
    # Test implementation
    pass
```

---

## 12. Testing Checklist

### For Every New Feature

**Before Implementation:**
- [ ] Write test plan
- [ ] Define test cases
- [ ] Identify edge cases
- [ ] Plan test data

**During Implementation:**
- [ ] Write tests first (TDD)
- [ ] Test happy path
- [ ] Test error cases
- [ ] Test edge cases
- [ ] Test with mocks

**After Implementation:**
- [ ] All tests pass
- [ ] Coverage >90%
- [ ] Integration tests added
- [ ] Performance acceptable
- [ ] Security reviewed

**Before Merge:**
- [ ] CI/CD passing
- [ ] Code review includes tests
- [ ] Documentation updated
- [ ] Backward compatibility verified

---

## 13. Success Metrics

### Test Quality Metrics

**Coverage:**
- Line coverage: >90%
- Branch coverage: >85%
- Function coverage: >95%

**Speed:**
- Unit tests: <5 seconds total
- Integration tests: <2 minutes total
- Full suite: <5 minutes total

**Reliability:**
- Flaky test rate: <1%
- Test failure rate: <5%
- False positive rate: <2%

**Maintenance:**
- Test to code ratio: 1:1 to 2:1
- Time to fix failing test: <1 hour
- Test update frequency: With every feature

---

## Appendix A: Testing Tools Reference

### Python Testing Tools

```bash
# Core testing
pytest==7.4.0           # Test runner
pytest-cov==4.1.0       # Coverage
pytest-mock==3.11.1     # Mocking
pytest-asyncio==0.21.0  # Async tests
pytest-xdist==3.3.1     # Parallel execution

# Mocking & fixtures
responses==0.23.1       # HTTP mocking
freezegun==1.2.2        # Time mocking
faker==19.3.1           # Fake data
factory-boy==3.3.0      # Factory fixtures

# Code quality
ruff==0.1.6            # Linting
mypy==1.7.1            # Type checking
bandit==1.7.5          # Security linting
```

### JavaScript/TypeScript Testing Tools

```json
{
  "vitest": "^1.0.0",
  "@testing-library/react": "^14.0.0",
  "@testing-library/jest-dom": "^6.1.0",
  "@testing-library/user-event": "^14.5.0",
  "msw": "^2.0.0",
  "playwright": "^1.40.0"
}
```

---

## Appendix B: Example Test Suites

See `tests/` directory for complete examples:
- `tests/unit/` - Unit test examples
- `tests/integration/` - Integration test examples
- `tests/e2e/` - End-to-end test examples
- `tests/fixtures/` - Shared fixtures and test data

---

## Summary

**This testing strategy provides:**

✅ **Comprehensive coverage** - Unit, integration, E2E, performance, security  
✅ **Clear guidelines** - What to test, how to test, when to test  
✅ **Practical examples** - Real test code for all scenarios  
✅ **CI/CD integration** - Automated testing on every commit  
✅ **Backward compatibility** - Ensure no regressions  
✅ **Mock strategies** - Fast, reliable tests without external dependencies  
✅ **Quality metrics** - Measurable success criteria  

**Ready for implementation with high confidence!**

---

**Last Updated:** December 11, 2025  
**Version:** 1.0  
**Status:** Ready for Review
