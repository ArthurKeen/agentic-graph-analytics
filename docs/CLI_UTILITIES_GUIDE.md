# CLI Utilities Guide

The graph-analytics-ai library includes command-line utilities for common database and authentication tasks.

---

## Available Utilities

### 1. OASIS Token Helper
**Module:** `graph_analytics_ai.auth.oasis_token_helper`  
**Purpose:** Manage ArangoDB AMP authentication tokens with intelligent caching

### 2. GAE Cleanup
**Module:** `graph_analytics_ai.cli.gae_cleanup`  
**Purpose:** List and delete Graph Analytics Engine (GAE) instances

### 3. Connection Tester
**Module:** `graph_analytics_ai.cli.test_connection`  
**Purpose:** Test and verify ArangoDB database connections

---

## 1. OASIS Token Helper

Manages ArangoDB Managed Platform (AMP) authentication tokens with automatic caching to avoid frequent `oasisctl` calls and handle certificate issues.

### Quick Start

```python
from graph_analytics_ai.auth import get_or_refresh_token

# Get or refresh token (uses cache if valid)
token = get_or_refresh_token()

# Force refresh
token = get_or_refresh_token(force_refresh=True)
```

### Command Line Usage

```bash
# Get or refresh token
python -m graph_analytics_ai.auth.oasis_token_helper

# Show token status
python -m graph_analytics_ai.auth.oasis_token_helper --status

# Force refresh (ignore cache)
python -m graph_analytics_ai.auth.oasis_token_helper --refresh

# Clear cached token
python -m graph_analytics_ai.auth.oasis_token_helper --clear

# Quiet mode (only output token for scripting)
python -m graph_analytics_ai.auth.oasis_token_helper --quiet

# Export to environment
export OASIS_TOKEN=$(python -m graph_analytics_ai.auth.oasis_token_helper --quiet)
```

### Features

- **Automatic Caching**: Tokens cached for 22 hours (refreshed 2 hours before expiry)
- **Multiple Sources**: Environment variable, cache, oasisctl, or manual input
- **Certificate Handling**: Detects and handles certificate verification errors
- **Status Monitoring**: Check token age and expiration

### Environment Variables

**Required for token generation:**
```bash
export OASIS_KEY_ID="your_api_key_id"
export OASIS_KEY_SECRET="your_api_key_secret"
```

**Optional:**
```bash
# Pre-existing token (bypasses generation)
export OASIS_TOKEN="your_token"

# Custom cache directory
export OASIS_TOKEN_CACHE_DIR="$HOME/my_cache"
```

### Python API

```python
from graph_analytics_ai.auth import TokenHelper

# Create helper with custom cache
helper = TokenHelper(cache_dir="/custom/path")

# Get token
token = helper.get_or_refresh_token()

# Show status
helper.show_status()

# Clear cache
helper.clear_cache()

# Manual token input
token = helper.get_token_manual()
```

### Integration Example

```python
#!/usr/bin/env python3
import os
from graph_analytics_ai.auth import get_or_refresh_token

def main():
    # Ensure we have a valid token
    token = get_or_refresh_token()
    if not token:
        print("Error: Failed to obtain OASIS token")
        return 1
    
    os.environ["OASIS_TOKEN"] = token
    
    # Now run your workflow
    from graph_analytics_ai.ai.workflow import run_agentic_workflow
    
    result = run_agentic_workflow(
        requirements_document="requirements.md",
        graph_name="my_graph"
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## 2. GAE Cleanup

List and delete Graph Analytics Engine (GAE) instances to manage resources and costs.

### Command Line Usage

```bash
# Run cleanup utility
python -m graph_analytics_ai.cli.gae_cleanup
```

### What It Does

1. Lists all GAE engines in your AMP deployment
2. Shows engine ID, size, and status
3. Prompts for confirmation before deletion
4. Deletes all engines if confirmed

### Example Output

```
🔍 Checking for running GAE engines...

Found 2 engine(s):

  Engine ID: 12345-abcde
  Size: s
  Status: running

  Engine ID: 67890-fghij
  Size: m
  Status: stopped

🗑️  Delete all engines? (yes/no): yes

Deleting engines...
  Deleting 12345-abcde...
  ✓ Deleted 12345-abcde
  Deleting 67890-fghij...
  ✓ Deleted 67890-fghij

✅ Cleanup complete!
```

### Python API

```python
from graph_analytics_ai.gae_connection import GAEManager

# Initialize manager
gae = GAEManager()

# List engines
engines = gae.list_engines()
for engine in engines:
    print(f"Engine: {engine['id']} - {engine['status']}")

# Delete specific engine
gae.delete_engine(engine_id)
```

### Use Cases

- Clean up after analysis runs
- Manage costs by removing unused engines
- Reset environment for testing
- Troubleshoot stuck engines

---

## 3. Connection Tester

Test and verify ArangoDB database connections with detailed diagnostics.

### Command Line Usage

```bash
# Test connection
python -m graph_analytics_ai.cli.test_connection
```

### What It Checks

1. ✅ Current directory
2. ✅ .env file exists
3. ✅ Environment variables loaded
4. ✅ Database connection successful
5. ✅ Collections accessible
6. ✅ User vs system collections count

### Example Output

```
======================================================================
DATABASE CONNECTION TEST
======================================================================

📁 Current Directory: /Users/you/my-project

✅ .env file found

📋 Environment Configuration:
   Database: my_database
   Endpoint: https://cluster.arangodb.cloud:8529
   User: root

======================================================================
ATTEMPTING CONNECTION...
======================================================================

✅ Successfully connected to ArangoDB!
   Database Name: my_database
   Total Collections: 15
     - User Collections: 10
     - System Collections: 5

   Sample User Collections:
      - Device
      - IP
      - AppProduct
      - Site
      - InstalledApp
      - household_components
      - uc_001_results
      - uc_s01_results
      - uc_s02_results
      - uc_s03_results

✅ ✅ SUCCESS! Connected to database: my_database

======================================================================
✅ CONNECTION TEST PASSED
======================================================================
```

### Python API

```python
from graph_analytics_ai.cli.test_connection import test_connection

# Run connection test
success = test_connection()

if success:
    print("Connection verified!")
else:
    print("Connection failed - check configuration")
```

### Troubleshooting

**Error: .env file not found**
```bash
# Create .env file with credentials
cp .env.example .env
# Edit with your credentials
```

**Error: Cannot import graph_analytics_ai**
```bash
# Install library
pip install graph-analytics-ai
# Or for local development:
pip install -e /path/to/agentic-graph-analytics
```

**Error: Connection failed**
- Check .env credentials
- Verify endpoint is reachable
- Confirm database name exists
- Test username/password

---

## Common Workflows

### Complete Setup and Test

```bash
# 1. Install library
pip install graph-analytics-ai

# 2. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 3. Get authentication token
python -m graph_analytics_ai.auth.oasis_token_helper

# 4. Test connection
python -m graph_analytics_ai.cli.test_connection

# 5. Run your analysis
python your_workflow.py
```

### CI/CD Integration

```yaml
# .github/workflows/analysis.yml
env:
  OASIS_TOKEN: ${{ secrets.OASIS_TOKEN }}
  ARANGO_ENDPOINT: ${{ secrets.ARANGO_ENDPOINT }}
  ARANGO_DATABASE: ${{ secrets.ARANGO_DATABASE }}
  ARANGO_USER: ${{ secrets.ARANGO_USER }}
  ARANGO_PASSWORD: ${{ secrets.ARANGO_PASSWORD }}

steps:
  - name: Test Connection
    run: python -m graph_analytics_ai.cli.test_connection
    
  - name: Run Analysis
    run: python scripts/run_analysis.py
    
  - name: Cleanup GAE
    if: always()
    run: python -m graph_analytics_ai.cli.gae_cleanup
```

### Development Script Template

```python
#!/usr/bin/env python3
"""
My Analysis Script with built-in utilities
"""
import os
import sys
from graph_analytics_ai.auth import get_or_refresh_token
from graph_analytics_ai.cli.test_connection import test_connection

def main():
    print("="*70)
    print("MY ANALYSIS WORKFLOW")
    print("="*70)
    
    # 1. Get authentication token
    print("\n1. Authenticating...")
    token = get_or_refresh_token()
    if not token:
        print("❌ Failed to obtain token")
        return 1
    os.environ["OASIS_TOKEN"] = token
    print("✅ Token obtained")
    
    # 2. Test connection
    print("\n2. Testing database connection...")
    if not test_connection():
        print("❌ Connection test failed")
        return 1
    print("✅ Connection verified")
    
    # 3. Run your analysis
    print("\n3. Running analysis...")
    from graph_analytics_ai.ai.workflow import run_agentic_workflow
    
    result = run_agentic_workflow(
        requirements_document="requirements.md",
        graph_name="my_graph"
    )
    
    print("✅ Analysis complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## Best Practices

### Token Management

1. **Cache tokens locally** - Reduces API calls and avoids rate limits
2. **Use environment variables in CI/CD** - Don't generate tokens in pipelines
3. **Check token status regularly** - Avoid expired token errors
4. **Secure your cache directory** - Default `~/.cache/oasis` has restricted permissions

### Connection Testing

1. **Test before long-running workflows** - Catch configuration errors early
2. **Use in setup scripts** - Verify environment before deployment
3. **Add to CI/CD pipelines** - Ensure infrastructure is ready

### GAE Cleanup

1. **Clean up after workflows** - Avoid unnecessary costs
2. **Use in CI/CD cleanup steps** - Don't leave engines running
3. **Check before starting** - Avoid conflicts with existing engines

---

## Troubleshooting

### Issue: "Operation not permitted" on .env file

**Solution**: Run with proper permissions or outside sandbox
```bash
python -m graph_analytics_ai.cli.test_connection
```

### Issue: Certificate verification error (macOS)

**Solution**: Use manual token input or set certificate path
```bash
export SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())")
python -m graph_analytics_ai.auth.oasis_token_helper
```

### Issue: GAE engines not found

**Solution**: Check your AMP deployment and credentials
```python
from graph_analytics_ai.gae_connection import GAEManager
gae = GAEManager()
print(f"GAE Endpoint: {gae.endpoint}")
print(f"Deployment ID: {gae.deployment_id}")
```

---

## Summary

The graph-analytics-ai CLI utilities provide:

✅ **Token Management** - Automatic caching and refresh  
✅ **Connection Testing** - Verify setup before running workflows  
✅ **Resource Cleanup** - Manage GAE engines and costs  
✅ **Developer Friendly** - Easy to integrate into scripts and CI/CD  
✅ **Production Ready** - Error handling and helpful diagnostics

For more examples and advanced usage, see:
- [OASIS Token Helper Guide](OASIS_TOKEN_HELPER_GUIDE.md) (legacy - being updated)
- [Environment Variables](ENVIRONMENT_VARIABLES.md)
- [Quick Reference](QUICK_REFERENCE.md)
