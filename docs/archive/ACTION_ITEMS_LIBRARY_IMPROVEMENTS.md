# Action Items: Library Improvements from dnb_gae

## Current Status

All three improvements from `dnb_gae` migration have been **implemented in code**, but we need to:

1.  **Verify** the implementations work correctly
2.  **Add tests** to ensure they work as expected
3.  **Create GitHub issue** to document and track these improvements

---

## What Needs to Be Done

### 1. Verify `.env` File Loading Priority  **CODE DONE** →  **NEEDS TESTING**

**What was implemented:**
- `load_env_vars()` now checks current working directory first, then library root

**What needs to be done:**
- [ ] **Test 1:** Create a `.env` file in a test project root and verify it loads
- [ ] **Test 2:** Verify fallback to library root works when project `.env` doesn't exist
- [ ] **Test 3:** Add unit test to `tests/test_config.py` to verify this behavior

**Test to add:**
```python
def test_load_env_vars_prioritizes_cwd(mock_env_amp, tmp_path):
    """Test that .env in current working directory is loaded first."""
    # Create .env in temporary directory (simulating project root)
    test_env = tmp_path / '.env'
    test_env.write_text('TEST_VAR=from_cwd\n')
    
    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        from graph_analytics_ai.config import load_env_vars
        load_env_vars()
        assert os.getenv('TEST_VAR') == 'from_cwd'
    finally:
        os.chdir(original_cwd)
```

---

### 2. Verify Config Masking Fix  **CODE DONE** →  **NEEDS TESTING**

**What was implemented:**
- `get_gae_config()` now uses `mask_secrets=False` to return actual values

**What needs to be done:**
- [ ] **Test 1:** Verify `get_gae_config()` returns actual API key (not `***MASKED***`)
- [ ] **Test 2:** Verify `GAEManager` can authenticate with unmasked values
- [ ] **Test 3:** Add unit test to verify unmasked values are returned

**Test to add:**
```python
def test_get_gae_config_unmasks_secrets(mock_env_amp):
    """Test that get_gae_config() returns unmasked values for internal use."""
    from graph_analytics_ai.config import get_gae_config
    
    config = get_gae_config()
    
    # Should return actual values, not masked
    assert config['api_key_id'] != '***MASKED***'
    assert config['api_key_secret'] != '***MASKED***'
    assert len(config['api_key_id']) > 0
    assert len(config['api_key_secret']) > 0
    
    # But to_dict(mask_secrets=True) should still mask
    from graph_analytics_ai.config import GAEConfig
    config_obj = GAEConfig()
    masked = config_obj.to_dict(mask_secrets=True)
    assert masked['api_key_id'] == '***MASKED***'
```

---

### 3. Verify SSL Verification Parser  **CODE DONE** →  **NEEDS TESTING**

**What was implemented:**
- `parse_ssl_verify()` now handles both string and boolean inputs
- Type hint updated to `Union[str, bool]`

**What needs to be done:**
- [ ] **Test 1:** Verify boolean `True` is handled correctly
- [ ] **Test 2:** Verify boolean `False` is handled correctly
- [ ] **Test 3:** Verify string values still work
- [ ] **Test 4:** Add unit tests to `tests/test_config.py`

**Tests to add:**
```python
def test_parse_ssl_verify_boolean_true():
    """Test parse_ssl_verify() with boolean True."""
    from graph_analytics_ai.config import parse_ssl_verify
    assert parse_ssl_verify(True) == True

def test_parse_ssl_verify_boolean_false():
    """Test parse_ssl_verify() with boolean False."""
    from graph_analytics_ai.config import parse_ssl_verify
    assert parse_ssl_verify(False) == False

def test_parse_ssl_verify_string_values():
    """Test parse_ssl_verify() with string values."""
    from graph_analytics_ai.config import parse_ssl_verify
    assert parse_ssl_verify("true") == True
    assert parse_ssl_verify("false") == False
    assert parse_ssl_verify("1") == True
    assert parse_ssl_verify("0") == False
    assert parse_ssl_verify("yes") == True
    assert parse_ssl_verify("no") == False

def test_parse_ssl_verify_unexpected_type():
    """Test parse_ssl_verify() defaults to True for unexpected types."""
    from graph_analytics_ai.config import parse_ssl_verify
    assert parse_ssl_verify(None) == True  # Defaults to True
    assert parse_ssl_verify(123) == True  # Defaults to True
```

---

## Step-by-Step Action Plan

### Step 1: Add Tests (Priority: HIGH)

**File:** `tests/test_config.py`

**Tasks:**
1. Add test for `.env` file loading priority
2. Add test for config masking fix
3. Add tests for SSL verification parser (boolean handling)

**Estimated time:** 30-45 minutes

---

### Step 2: Run Tests (Priority: HIGH)

**Command:**
```bash
cd /Users/arthurkeen/code/graph-analytics-ai
pytest tests/test_config.py -v
```

**Expected:**
- All new tests pass
- No regressions in existing tests

---

### Step 3: Manual Verification (Priority: MEDIUM)

**Test 1: `.env` File Loading**
```bash
# Create a test project
mkdir /tmp/test_project
cd /tmp/test_project

# Create .env file
echo "TEST_VAR=from_project_root" > .env

# Test loading
python3 -c "
import os
os.chdir('/tmp/test_project')
from graph_analytics_ai.config import load_env_vars
load_env_vars()
print('TEST_VAR:', os.getenv('TEST_VAR'))
# Should print: TEST_VAR: from_project_root
"
```

**Test 2: Config Masking**
```bash
# Set environment variables
export GAE_DEPLOYMENT_MODE=amp
export ARANGO_GRAPH_API_KEY_ID=test-key-12345
export ARANGO_GRAPH_API_KEY_SECRET=test-secret-67890

# Test unmasked config
python3 -c "
from graph_analytics_ai.config import get_gae_config
config = get_gae_config()
print('API Key ID:', config['api_key_id'])
print('Is masked?', config['api_key_id'] == '***MASKED***')
# Should print actual key, not masked
"
```

**Test 3: SSL Verification Parser**
```bash
python3 -c "
from graph_analytics_ai.config import parse_ssl_verify
print('Boolean True:', parse_ssl_verify(True))
print('Boolean False:', parse_ssl_verify(False))
print('String true:', parse_ssl_verify('true'))
print('String false:', parse_ssl_verify('false'))
# All should work without errors
"
```

---

### Step 4: Create GitHub Issue (Priority: LOW)

**Action:**
1. Copy contents of `GITHUB_ISSUE_LIBRARY_IMPROVEMENTS.md`
2. Create new GitHub issue
3. Add labels: `bug`, `enhancement`, `config`, `testing`
4. Mark as ready for review after tests pass

---

## Summary

### What's Done 
- All three improvements implemented in code
- Type hints updated
- Code follows the pattern from `dnb_gae`

### What Needs to Be Done 
1. **Add unit tests** for all three improvements
2. **Run tests** to verify everything works
3. **Manual verification** with real scenarios
4. **Create GitHub issue** to document improvements

### Priority Order
1. **HIGH:** Add and run tests
2. **MEDIUM:** Manual verification
3. **LOW:** Create GitHub issue

---

## Quick Start

To get started immediately:

```bash
cd /Users/arthurkeen/code/graph-analytics-ai

# 1. Add tests to tests/test_config.py (see examples above)

# 2. Run tests
pytest tests/test_config.py::test_load_env_vars_prioritizes_cwd -v
pytest tests/test_config.py::test_get_gae_config_unmasks_secrets -v
pytest tests/test_config.py::test_parse_ssl_verify_boolean_true -v

# 3. If all pass, create GitHub issue
```

---

## Questions?

If you need clarification on any step, let me know!

