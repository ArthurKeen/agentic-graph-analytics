# Clear Action Plan: Library Improvements

## Problem Found

The code is implemented correctly, but:
1.  **One test is WRONG** - expects masked values but code returns unmasked
2.  **Missing test** for `.env` loading priority
3.  **Missing test** for SSL parser with boolean values

---

## What Needs to Be Done (In Order)

###  Step 1: Fix Broken Test (CRITICAL)

**File:** `tests/test_config.py`  
**Line:** ~208

**Current (WRONG):**
```python
def test_get_gae_config(self, mock_env_amp):
    """Test get_gae_config function."""
    config = get_gae_config()
    
    assert config['deployment_mode'] == 'amp'
    assert config['api_key_id'] == '***MASKED***'  #  WRONG - expects masked
    assert config['api_key_secret'] == '***MASKED***'  #  WRONG - expects masked
```

**Should be (CORRECT):**
```python
def test_get_gae_config(self, mock_env_amp):
    """Test get_gae_config function returns unmasked values for internal use."""
    config = get_gae_config()
    
    assert config['deployment_mode'] == 'amp'
    assert config['api_key_id'] != '***MASKED***'  #  Should be actual value
    assert config['api_key_secret'] != '***MASKED***'  #  Should be actual value
    assert len(config['api_key_id']) > 0  # Verify it's a real key
```

**Why:** The code now returns unmasked values (correct), but the test expects masked (wrong).

---

###  Step 2: Add Test for `.env` Loading Priority

**File:** `tests/test_config.py`  
**Add after existing tests:**

```python
def test_load_env_vars_prioritizes_cwd(tmp_path, monkeypatch):
    """Test that .env in current working directory is loaded first."""
    from graph_analytics_ai.config import load_env_vars
    import os
    
    # Create .env in temporary directory (simulating project root)
    test_env = tmp_path / '.env'
    test_env.write_text('TEST_VAR=from_cwd\n')
    
    # Change to temp directory
    monkeypatch.chdir(tmp_path)
    
    # Load env vars
    load_env_vars()
    
    # Verify it loaded from CWD
    assert os.getenv('TEST_VAR') == 'from_cwd'
```

**Why:** Need to verify the new priority logic works.

---

###  Step 3: Add Test for SSL Parser with Booleans

**File:** `tests/test_config.py`  
**Add after `test_parse_ssl_verify_false`:**

```python
def test_parse_ssl_verify_with_boolean(self):
    """Test parse_ssl_verify() handles boolean values."""
    from graph_analytics_ai.config import parse_ssl_verify
    
    # Test boolean True
    assert parse_ssl_verify(True) is True
    
    # Test boolean False
    assert parse_ssl_verify(False) is False
    
    # Verify string values still work (regression test)
    assert parse_ssl_verify('true') is True
    assert parse_ssl_verify('false') is False
```

**Why:** Existing tests only check strings, but code now handles booleans too.

---

###  Step 4: Run Tests

**Command:**
```bash
cd /Users/arthurkeen/code/graph-analytics-ai
pytest tests/test_config.py -v
```

**Expected:**
- All tests pass 
- No failures

---

###  Step 5: Create GitHub Issue

**Action:**
1. Copy contents from `GITHUB_ISSUE_LIBRARY_IMPROVEMENTS.md`
2. Create new GitHub issue
3. Update status to " Implemented, tests added and verified"
4. Add labels: `bug`, `enhancement`, `config`

---

## Summary

### What's Done 
- Code is implemented correctly
- All three improvements are in place

### What Needs Fixing 
1. **Fix broken test** - `test_get_gae_config` expects wrong values
2. **Add missing test** - `.env` loading priority
3. **Add missing test** - SSL parser with booleans

### Time Estimate
- Fix test: 2 minutes
- Add 2 tests: 10 minutes
- Run tests: 2 minutes
- Create issue: 5 minutes
- **Total: ~20 minutes**

---

## Quick Start

**Option 1: I can do it for you**
Just say "yes" and I'll:
1. Fix the broken test
2. Add the two missing tests
3. Run the tests
4. Show you the results

**Option 2: You do it**
1. Edit `tests/test_config.py`
2. Fix line ~208 (change `== '***MASKED***'` to `!= '***MASKED***'`)
3. Add the two test functions above
4. Run `pytest tests/test_config.py -v`

---

## Questions?

The main issue is: **one test is wrong and needs fixing**. The code is correct, but the test expects the old (wrong) behavior.

Would you like me to fix it now?

