# OASIS Token Helper Usage Guide

This helper script manages ArangoDB Managed Platform (AMP) authentication tokens with intelligent caching to avoid certificate issues with `oasisctl`.

## Quick Start

### Method 1: Direct Usage

```bash
# Get or refresh token (interactive)
python scripts/oasis_token_helper.py

# Export to environment
export OASIS_TOKEN=$(python scripts/oasis_token_helper.py --quiet)

# Now run your workflows
python scripts/run_household_analysis.py
```

### Method 2: Use in Python Code

```python
# At the top of your script
from scripts.oasis_token_helper import get_or_refresh_token
import os

# Get token and set environment variable
token = get_or_refresh_token()
if token:
    os.environ["OASIS_TOKEN"] = token
else:
    print("Failed to obtain token")
    exit(1)

# Now use graph-analytics-ai-platform normally
from graph_analytics_ai import GAEConnection
# ... rest of your code
```

## Features

### 1. Automatic Token Caching
- Tokens are cached for 22 hours (refreshed 2 hours before expiry)
- Cache location: `~/.cache/oasis/token.json`
- Reduces `oasisctl` calls to once per day

### 2. Multiple Token Sources
1. **Environment Variable** - Uses `OASIS_TOKEN` if already set
2. **Cache** - Uses cached token if valid
3. **oasisctl** - Generates new token with API credentials
4. **Manual Input** - Fallback for certificate issues

### 3. Certificate Error Handling
- Detects certificate verification errors
- Provides helpful troubleshooting steps
- Offers manual token input as fallback

### 4. Token Status Monitoring

```bash
# Check token status
python scripts/oasis_token_helper.py --status
```

Output:
```
OASIS Token Status
============================================================
Environment: Not set
Cached Token: Found
  Created: 2026-01-14 09:30:00
  Age: 2.5 hours
  Expires in: 21.5 hours
  Status: Valid
============================================================
```

## Command-Line Options

```bash
# Get or refresh token (default)
python scripts/oasis_token_helper.py

# Force refresh (ignore cache)
python scripts/oasis_token_helper.py --refresh

# Show token status
python scripts/oasis_token_helper.py --status

# Clear cached token
python scripts/oasis_token_helper.py --clear

# Quiet mode (only output token)
python scripts/oasis_token_helper.py --quiet
```

## Environment Variables

### Required for Token Generation
```bash
export OASIS_KEY_ID="your_api_key_id"
export OASIS_KEY_SECRET="your_api_key_secret"
```

### Optional
```bash
# Pre-existing token (bypasses generation)
export OASIS_TOKEN="your_token"

# Custom cache directory
export OASIS_TOKEN_CACHE_DIR="$HOME/my_cache"
```

## Handling Certificate Issues

If you encounter certificate errors with `oasisctl`:

### Option 1: Use Cached Token (Recommended)
```bash
# Generate token once (may need to do on different machine or with workarounds)
python scripts/oasis_token_helper.py

# Token is now cached for 24 hours
# All subsequent runs use the cache automatically
```

### Option 2: Manual Token Input
```bash
# Run the helper
python scripts/oasis_token_helper.py

# When oasisctl fails, choose manual input (y)
# Paste token from ArangoDB Cloud console or another machine
```

### Option 3: Update oasisctl
```bash
brew upgrade arangodb/tap/oasisctl
```

### Option 4: Certificate Path Workaround
```bash
# Set certificate path before running
export SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())")
python scripts/oasis_token_helper.py
```

## Integration Examples

### Example 1: Shell Script Wrapper

```bash
#!/bin/bash
# run_with_token.sh

# Ensure token is available
export OASIS_TOKEN=$(python scripts/oasis_token_helper.py --quiet)

if [ $? -ne 0 ]; then
    echo "Failed to obtain OASIS token"
    exit 1
fi

# Run your analysis
python scripts/run_household_analysis.py "$@"
```

### Example 2: Python Workflow

```python
#!/usr/bin/env python3
# run_analysis.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Get token
from scripts.oasis_token_helper import get_or_refresh_token

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
        graph_name="household_graph",
        output_dir="./output"
    )
    
    print(f"Workflow completed: {result}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Example 3: Makefile Integration

```makefile
# Makefile

# Ensure token is available before running any targets
.PHONY: ensure-token
ensure-token:
	@python scripts/oasis_token_helper.py --quiet > /dev/null || \
		(echo "Failed to obtain token" && exit 1)

# Run analysis with token
.PHONY: run-analysis
run-analysis: ensure-token
	@export OASIS_TOKEN=$$(python scripts/oasis_token_helper.py --quiet) && \
		python scripts/run_household_analysis.py

# Check token status
.PHONY: token-status
token-status:
	@python scripts/oasis_token_helper.py --status

# Refresh token
.PHONY: token-refresh
token-refresh:
	@python scripts/oasis_token_helper.py --refresh
```

## Troubleshooting

### Problem: "OASIS_KEY_ID and OASIS_KEY_SECRET environment variables required"

**Solution**: Set your API credentials
```bash
export OASIS_KEY_ID="your_key_id"
export OASIS_KEY_SECRET="your_key_secret"
```

### Problem: "oasisctl not found"

**Solution**: Install oasisctl
```bash
brew install arangodb/tap/oasisctl
```

### Problem: Certificate verification error (x509: OSStatus -26276)

**Solution**: Use manual token input or update oasisctl
```bash
# Option 1: Manual input
python scripts/oasis_token_helper.py
# Choose 'y' when prompted for manual input

# Option 2: Update
brew upgrade arangodb/tap/oasisctl
```

### Problem: Token expired during long-running workflow

**Solution**: The library automatically refreshes tokens. If you need to manually refresh:
```bash
python scripts/oasis_token_helper.py --refresh
```

## Security Notes

- Tokens are cached in `~/.cache/oasis/` with standard file permissions
- Tokens expire after 24 hours
- API credentials are never stored, only used to generate tokens
- Cache file contains: token, created_at, expires_at (no secrets)

## Advanced Usage

### Custom Cache Location

```python
from scripts.oasis_token_helper import TokenHelper
from pathlib import Path

# Use custom cache directory
helper = TokenHelper(cache_dir=Path("/tmp/my_cache"))
token = helper.get_or_refresh_token()
```

### Force Token Refresh

```python
from scripts.oasis_token_helper import get_or_refresh_token

# Force refresh even if cached token is valid
token = get_or_refresh_token(force_refresh=True)
```

### Programmatic Status Check

```python
from scripts.oasis_token_helper import TokenHelper

helper = TokenHelper()
helper.show_status()
```

## For CI/CD Environments

In CI/CD, use pre-generated tokens:

```yaml
# .github/workflows/analysis.yml
env:
  OASIS_TOKEN: ${{ secrets.OASIS_TOKEN }}

steps:
  - name: Run Analysis
    run: python scripts/run_household_analysis.py
```

No need to run the helper in CI - just set `OASIS_TOKEN` as a secret.
