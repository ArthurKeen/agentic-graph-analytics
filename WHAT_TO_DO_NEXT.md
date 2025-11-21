# What Needs to Be Done - Library Improvements

## TL;DR

**Status:** Code is implemented , but we need to:
1. **Add missing tests** (30 minutes)
2. **Verify everything works** (15 minutes)
3. **Create GitHub issue** (5 minutes)

---

## The Three Improvements

All three improvements from `dnb_gae` are **already in the code**, but we need to verify they work:

### 1. `.env` File Loading Priority
-  **Code:** Implemented (checks current directory first)
-  **Test:** Need to add test

### 2. Config Masking Fix
-  **Code:** Implemented (`mask_secrets=False`)
-  **Test:** Need to verify test covers this

### 3. SSL Verification Parser
-  **Code:** Implemented (handles booleans)
-  **Test:** Need to add test for boolean handling

---

## Action Items (In Order)

###  Step 1: Check What Tests Already Exist

**Command:**
```bash
cd /Users/arthurkeen/code/graph-analytics-ai
grep -n "def test" tests/test_config.py
```

**What to look for:**
- Test for `.env` loading priority? (probably missing)
- Test for config masking? (check if it verifies unmasked values)
- Test for SSL parser with booleans? (check if it tests `True`/`False`)

---

###  Step 2: Add Missing Tests

**File to edit:** `tests/test_config.py`

**Test 1: `.env` File Loading Priority** (if missing)
```python
def test_load_env_vars_prioritizes_cwd(tmp_path, monkeypatch):
    """Test that .env in current working directory is loaded first."""
    from graph_analytics_ai.config import load_env_vars
    import os
    
    # Create .env in temporary directory
    test_env = tmp_path / '.env'
    test_env.write_text('TEST_VAR=from_cwd\n')
    
    # Change to temp directory
    monkeypatch.chdir(tmp_path)
    
    # Load env vars
    load_env_vars()
    
    # Verify it loaded from CWD
    assert os.getenv('TEST_VAR') == 'from_cwd'
```

**Test 2: Config Masking** (if not already testing unmasked values)
```python
def test_get_gae_config_returns_unmasked_values(mock_env_amp):
    """Test that get_gae_config() returns actual values, not masked."""
    from graph_analytics_ai.config import get_gae_config
    
    config = get_gae_config()
    
    # Should return actual values
    assert config['api_key_id'] != '***MASKED***'
    assert config['api_key_secret'] != '***MASKED***'
    assert len(config['api_key_id']) > 0
```

**Test 3: SSL Parser with Booleans** (if missing)
```python
def test_parse_ssl_verify_with_boolean(mock_env_amp):
    """Test parse_ssl_verify() handles boolean values."""
    from graph_analytics_ai.config import parse_ssl_verify
    
    # Test boolean True
    assert parse_ssl_verify(True) == True
    
    # Test boolean False
    assert parse_ssl_verify(False) == False
    
    # Test string values still work
    assert parse_ssl_verify("true") == True
    assert parse_ssl_verify("false") == False
```

---

###  Step 3: Run Tests

**Command:**
```bash
cd /Users/arthurkeen/code/graph-analytics-ai
pytest tests/test_config.py -v
```

**Expected result:**
- All tests pass 
- No errors or failures

---

###  Step 4: Quick Manual Verification (Optional)

**Test 1: `.env` Loading**
```bash
# Create test .env
cd /tmp
echo "TEST_VAR=test123" > .env

# Test it loads
python3 -c "
import os
os.chdir('/tmp')
from graph_analytics_ai.config import load_env_vars
load_env_vars()
print('Loaded:', os.getenv('TEST_VAR'))
"
# Should print: Loaded: test123
```

**Test 2: Config Masking**
```bash
export GAE_DEPLOYMENT_MODE=amp
export ARANGO_GRAPH_API_KEY_ID=my-test-key-12345

python3 -c "
from graph_analytics_ai.config import get_gae_config
config = get_gae_config()
print('Key:', config['api_key_id'])
print('Is masked?', '***MASKED***' in config['api_key_id'])
"
# Should print actual key, not masked
```

**Test 3: SSL Parser**
```bash
python3 -c "
from graph_analytics_ai.config import parse_ssl_verify
print('Bool True:', parse_ssl_verify(True))
print('Bool False:', parse_ssl_verify(False))
print('String true:', parse_ssl_verify('true'))
"
# Should all work without errors
```

---

###  Step 5: Create GitHub Issue

**Action:**
1. Go to GitHub repository
2. Click "New Issue"
3. Copy contents from `GITHUB_ISSUE_LIBRARY_IMPROVEMENTS.md`
4. Add labels: `bug`, `enhancement`, `config`
5. Mark as "Ready for Review" or "Done" (if tests pass)

---

## Summary Checklist

- [ ] Check existing tests in `tests/test_config.py`
- [ ] Add test for `.env` loading priority (if missing)
- [ ] Add/update test for config masking (verify unmasked values)
- [ ] Add test for SSL parser with booleans (if missing)
- [ ] Run `pytest tests/test_config.py -v` and verify all pass
- [ ] (Optional) Quick manual verification
- [ ] Create GitHub issue using `GITHUB_ISSUE_LIBRARY_IMPROVEMENTS.md`

---

## Estimated Time

- **Check existing tests:** 5 minutes
- **Add missing tests:** 20-30 minutes
- **Run and verify tests:** 5 minutes
- **Manual verification (optional):** 10 minutes
- **Create GitHub issue:** 5 minutes

**Total:** ~45-60 minutes

---

## Need Help?

If you want me to:
1. **Check what tests exist** - I can do this
2. **Add the missing tests** - I can do this
3. **Run the tests** - I can do this
4. **Create the GitHub issue** - I can provide the content (already done)

Just let me know what you'd like me to do!

