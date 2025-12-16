# Testing Guide

**Version:** 3.0.0  
**Last Updated:** December 12, 2025  
**Coverage:** 90%+

---

##  Testing Overview

### Current Status

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Test Coverage** | 90%+ | 80%+ |  Excellent |
| **Total Tests** | 150+ | 100+ |  Exceeds |
| **Unit Tests** | 130+ | - |  Good |
| **Integration Tests** | 20+ | - |  Good |
| **Test Runtime** | < 30s | < 60s |  Fast |

---

##  Quick Start

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=graph_analytics_ai tests/

# Run specific test file
pytest tests/unit/ai/agents/test_base.py

# Run specific test
pytest tests/unit/ai/agents/test_base.py::test_agent_creation

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Coverage Report

```bash
# Generate coverage report
pytest --cov=graph_analytics_ai --cov-report=html tests/

# View report
open htmlcov/index.html
```

---

##  Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── ai/
│   │   ├── agents/         # Agent tests
│   │   ├── llm/            # LLM provider tests
│   │   ├── schema/         # Schema analysis tests
│   │   ├── documents/      # Document processing tests
│   │   ├── execution/      # Execution tests
│   │   ├── reporting/      # Reporting tests
│   │   ├── templates/      # Template tests
│   │   └── workflow/       # Workflow tests
│   └── ...
├── integration/             # Integration tests
│   └── test_complete_workflow.py
└── fixtures/                # Test data
    ├── sample_documents/
    └── sample_schemas/
```

---

## ✍️ Writing Tests

### Test Naming Convention

```python
def test_<component>_<scenario>_<expected_result>():
    """Test that <component> <expected_result> when <scenario>."""
    pass

# Examples:
def test_schema_extractor_returns_collections_when_graph_exists():
    """Test that schema extractor returns collections when graph exists."""
    
def test_agent_process_raises_error_when_message_invalid():
    """Test that agent process raises error when message invalid."""
```

### Test Structure (AAA Pattern)

```python
def test_example():
    # Arrange - Set up test data
    schema = create_test_schema()
    analyzer = SchemaAnalyzer(mock_llm)
    
    # Act - Execute the code under test
    result = analyzer.analyze(schema)
    
    # Assert - Verify the results
    assert result.domain == "E-commerce"
    assert result.complexity_score > 0
```

### Using Fixtures

```python
# conftest.py
import pytest

@pytest.fixture
def mock_db():
    """Mock database connection."""
    db = Mock()
    db.version.return_value = {"version": "3.10.0"}
    return db

# test file
def test_with_fixture(mock_db):
    """Test using fixture."""
    extractor = SchemaExtractor(mock_db)
    result = extractor.extract()
    assert result is not None
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch, MagicMock

# Mock LLM provider
@patch('module.LLMProvider')
def test_with_mock_llm(mock_llm_class):
    mock_llm = Mock()
    mock_llm.generate.return_value = Mock(content="test response")
    mock_llm_class.return_value = mock_llm
    
    # Test code here

# Mock database
@patch('module.get_db_connection')
def test_with_mock_db(mock_get_db):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    
    # Test code here
```

---

##  Test Coverage Requirements

### Minimum Coverage by Component

| Component | Minimum | Current |
|-----------|---------|---------|
| **Agents** | 85% | 92%  |
| **LLM** | 80% | 88%  |
| **Schema** | 85% | 90%  |
| **Documents** | 80% | 87%  |
| **Execution** | 85% | 91%  |
| **Reporting** | 80% | 89%  |
| **Templates** | 85% | 90%  |
| **Workflow** | 85% | 93%  |

### What to Test

**Always Test:**
-  Happy path (normal operation)
-  Error handling
-  Edge cases
-  Boundary conditions
-  Invalid input handling

**Example:**
```python
class TestSchemaExtractor:
    def test_extract_success(self, mock_db):
        """Test successful extraction."""
        # Happy path
        
    def test_extract_empty_graph(self, mock_db):
        """Test extraction with empty graph."""
        # Edge case
        
    def test_extract_invalid_connection(self):
        """Test extraction with invalid connection."""
        # Error handling
        
    def test_extract_with_large_graph(self, mock_db):
        """Test extraction with 10M+ nodes."""
        # Boundary condition
```

---

##  Test Types

### 1. Unit Tests

Test individual components in isolation.

```python
# tests/unit/ai/agents/test_base.py
def test_agent_create_message():
    """Test message creation."""
    agent = TestAgent("test", mock_llm)
    message = agent.create_message(
        to_agent="other",
        message_type="task",
        content={"data": "value"}
    )
    
    assert message.from_agent == "test"
    assert message.to_agent == "other"
    assert message.content["data"] == "value"
```

### 2. Integration Tests

Test components working together.

```python
# tests/integration/test_workflow.py
def test_complete_linear_workflow():
    """Test complete workflow execution."""
    # Set up real components
    db = get_db_connection()
    orchestrator = WorkflowOrchestrator(...)
    
    # Run workflow
    result = orchestrator.run_complete_workflow(...)
    
    # Verify end-to-end
    assert result.success
    assert len(result.reports) > 0
```

### 3. Parametrized Tests

Test multiple scenarios.

```python
@pytest.mark.parametrize("algorithm,expected_type", [
    ("pagerank", AlgorithmType.CENTRALITY),
    ("louvain", AlgorithmType.COMMUNITY),
    ("shortest_path", AlgorithmType.PATHFINDING),
])
def test_algorithm_type_detection(algorithm, expected_type):
    """Test algorithm type detection."""
    result = detect_algorithm_type(algorithm)
    assert result == expected_type
```

---

##  Test Utilities

### Creating Test Data

```python
# tests/conftest.py
def create_test_schema():
    """Create test schema."""
    return GraphSchema(
        vertex_collections=[
            CollectionInfo(name="users", type=CollectionType.VERTEX),
            CollectionInfo(name="products", type=CollectionType.VERTEX),
        ],
        edge_collections=[
            CollectionInfo(name="purchased", type=CollectionType.EDGE),
        ],
        total_documents=1000,
        total_edges=500
    )

def create_test_requirements():
    """Create test requirements."""
    return ExtractedRequirements(
        domain="Test",
        summary="Test requirements",
        objectives=[...],
        requirements=[...]
    )
```

### Assertion Helpers

```python
def assert_valid_schema(schema):
    """Assert schema is valid."""
    assert schema is not None
    assert len(schema.vertex_collections) > 0
    assert schema.total_documents > 0

def assert_successful_execution(result):
    """Assert execution was successful."""
    assert result.success
    assert result.job is not None
    assert result.job.status == "completed"
```

---

##  Pre-Commit Checklist

Before committing code:

### Run Tests
```bash
# 1. Run all tests
pytest

# 2. Check coverage
pytest --cov=graph_analytics_ai tests/

# 3. Verify coverage meets minimums
pytest --cov=graph_analytics_ai --cov-fail-under=80 tests/
```

### Check Code Quality
```bash
# 4. Format code
black graph_analytics_ai/ tests/

# 5. Check types (if mypy installed)
mypy graph_analytics_ai/

# 6. Lint (if pylint installed)
pylint graph_analytics_ai/
```

### Verify Changes
```bash
# 7. Run only affected tests
pytest tests/unit/ai/agents/  # If you changed agents

# 8. Run integration tests
pytest tests/integration/

# 9. Check for regressions
pytest --lf  # Run last failed tests
```

---

##  Debugging Tests

### Running Failed Tests

```bash
# Re-run last failed tests
pytest --lf

# Re-run last failed, stop on first failure
pytest --lf -x

# Show local variables on failure
pytest -l

# Enter debugger on failure
pytest --pdb
```

### Verbose Output

```bash
# Show print statements
pytest -s

# Very verbose
pytest -vv

# Show test durations
pytest --durations=10
```

### Filtering Tests

```bash
# Run tests matching pattern
pytest -k "schema"

# Run specific markers
pytest -m "slow"

# Skip specific markers
pytest -m "not slow"
```

---

##  Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    
    - name: Install dependencies
      run: |
        pip install -e .
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=graph_analytics_ai --cov-report=xml tests/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

##  Testing Best Practices

### DO 

- Write tests for all new features
- Test error conditions
- Use descriptive test names
- Keep tests fast (< 1s each)
- Mock external dependencies
- Test edge cases
- Maintain 80%+ coverage
- Run tests before committing

### DON'T 

- Test implementation details
- Write tests that depend on each other
- Use real external services in unit tests
- Ignore failing tests
- Skip error case testing
- Hard-code test data paths
- Commit without running tests

---

##  Common Testing Patterns

### Testing Exceptions

```python
def test_raises_error_on_invalid_input():
    """Test error handling."""
    with pytest.raises(ValueError, match="Invalid input"):
        process_invalid_data()
```

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async operation."""
    result = await async_function()
    assert result is not None
```

### Testing with Temp Files

```python
import tempfile

def test_with_temp_file():
    """Test with temporary file."""
    with tempfile.NamedTemporaryFile(mode='w') as f:
        f.write("test data")
        f.flush()
        result = process_file(f.name)
        assert result is not None
```

---

##  Test Metrics

### Current Stats (v3.0.0)

- **Total Tests:** 150+
- **Unit Tests:** 130+
- **Integration Tests:** 20+
- **Coverage:** 90%+
- **Avg Test Time:** 0.2s
- **Total Test Time:** < 30s

### Coverage by Module

```
graph_analytics_ai/
├── ai/
│   ├── agents/          92% 
│   ├── llm/             88% 
│   ├── schema/          90% 
│   ├── documents/       87% 
│   ├── execution/       91% 
│   ├── reporting/       89% 
│   ├── templates/       90% 
│   └── workflow/        93% 
├── db_connection.py     85% 
├── gae_orchestrator.py  88% 
└── config.py            92% 

Overall: 90%+ 
```

---

##  Next Steps

### Planned Improvements (v3.1.0)

1. **Performance Tests**
   - Benchmark critical paths
   - Load testing
   - Memory profiling

2. **Property-Based Testing**
   - Use hypothesis library
   - Generate test cases automatically

3. **Mutation Testing**
   - Verify test quality
   - Find untested code paths

4. **Contract Testing**
   - API contract validation
   - Integration contract tests

---

##  Getting Help

**Questions about testing?**

- Check existing tests for examples
- See `tests/conftest.py` for fixtures
- Review test utilities
- Ask in GitHub Discussions

---

**Maintained By:** Development Team  
**Last Updated:** December 12, 2025  
**Test Coverage:** 90%+ 

