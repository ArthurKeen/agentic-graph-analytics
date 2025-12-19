# Integration Tests

This directory contains integration tests that require real external services:
- LLM providers (OpenRouter/Gemini)
- ArangoDB database
- GAE (Graph Analytics Engine)

## Running Integration Tests

Integration tests are marked with `@pytest.mark.integration` and are **skipped by default**.

### Run All Tests (Unit + Integration)
```bash
pytest tests/ --run-integration
```

### Run Only Integration Tests
```bash
pytest tests/integration/ -v
```

### Run Specific Integration Test
```bash
pytest tests/integration/test_workflow_e2e.py::test_complete_workflow -v
```

## Test Categories

### E2E Workflow Tests (`test_workflow_e2e.py`)
Tests the complete agentic workflow from business requirements to generated outputs.

**Requirements:**
- `OPENROUTER_API_KEY` environment variable
- `ARANGO_ENDPOINT`, `ARANGO_DATABASE`, `ARANGO_PASSWORD` environment variables
- Test database with sample data

### GAE Execution Tests (`test_gae_execution_e2e.py`)
Tests actual GAE algorithm execution with real engines.

**Requirements:**
- `ARANGO_GRAPH_TOKEN` or ArangoDB credentials
- GAE access (AMP or self-managed)
- Test database with graph data

### LLM Integration Tests (`test_llm_integration.py`)
Tests LLM provider interactions.

**Requirements:**
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY`

## Test Configuration

Tests use environment variables for configuration. Create a `.env.test` file:

```bash
# LLM Configuration
OPENROUTER_API_KEY=your_key_here
LLM_MODEL=google/gemini-flash-1.5

# Database Configuration (for testing)
ARANGO_ENDPOINT=http://localhost:8529
ARANGO_DATABASE=graph-analytics-ai-test
ARANGO_USER=root
ARANGO_PASSWORD=test_password

# GAE Configuration (for GAE tests)
ARANGO_GRAPH_TOKEN=your_token_here
GAE_DEPLOYMENT_MODE=amp
```

## Test Data

Test fixtures are in `fixtures/` directory:
- `test_use_case.md` - Sample business requirements
- `test_database_setup.py` - Script to create test database
- `sample_graph_data.json` - Sample graph for testing

## CI/CD Integration

To run integration tests in CI/CD:

1. Set environment variables as secrets
2. Use test database (not production!)
3. Run with appropriate markers:
   ```bash
   pytest tests/ -m "not slow" --run-integration
   ```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Always clean up test data/engines
3. **Timeouts**: Set reasonable timeouts for external calls
4. **Retry**: Add retry logic for transient failures
5. **Cost**: Be mindful of API/engine costs in tests

## Troubleshooting

### Tests Skipped
- Check that `--run-integration` flag is set
- Verify environment variables are set

### Connection Errors
- Verify database is running and accessible
- Check credentials in environment variables
- Ensure network connectivity

### Timeout Errors
- Increase timeout values in test configuration
- Check service availability
- Review service logs

## Contributing

When adding new integration tests:
1. Mark with `@pytest.mark.integration`
2. Add docstring explaining what is being tested
3. Include setup/teardown for test resources
4. Document required environment variables
5. Add to this README

