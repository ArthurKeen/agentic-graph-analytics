# Environment File Setup Guide

## Problem
You have production credentials in the library project's `.env` file, but you need:
1. **Library project** - Test credentials for library development
2. **Customer project** - Production credentials for customer use case

## Solution: Separate the Credentials

### Step 1: Backup Current .env (if it contains production credentials)

```bash
cd ~/code/graph-analytics-ai-platform
cp .env .env.production.backup
```

### Step 2: Update Library Project .env (Test Credentials)

Edit `~/code/graph-analytics-ai-platform/.env`:

```bash
# Test credentials for library development/testing
ARANGO_DATABASE=graph-analytics-ai
ARANGO_USER=root
ARANGO_PASSWORD=your_test_password
ARANGO_ENDPOINT=https://your-test-cluster.arangodb.cloud:8529

# GAE Configuration
GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_test_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_test_api_key_secret

# LLM Configuration
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-flash-1.5-8b

# Optional settings
ARANGO_VERIFY_SSL=true
ARANGO_TIMEOUT=30
LOG_LEVEL=INFO
```

### Step 3: Create Customer Project .env (Production Credentials)

Edit `~/code/your-customer-project/.env`:

```bash
# Customer Production Database
ARANGO_DATABASE=your_production_database
ARANGO_USER=root
ARANGO_PASSWORD=your_production_password
ARANGO_ENDPOINT=https://your-production-cluster.arangodb.cloud:8529

# GAE Configuration
GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_production_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_production_api_key_secret

# LLM Configuration
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-flash-1.5-8b

# Customer-Specific Settings (optional - not read by library)
GRAPH_NAME=YourGraphName
MAX_EXECUTIONS=3
CHECKPOINT_DIR=./outputs/checkpoints
REPORTS_DIR=./outputs/generated_reports
STATE_DIR=./outputs
LOG_LEVEL=INFO

# Optional SSL and timeout settings
ARANGO_VERIFY_SSL=true
ARANGO_TIMEOUT=30
```

### Step 4: Create .env.example Files (For Version Control)

**Library project** (`~/code/graph-analytics-ai-platform/.env.example`):

```bash
# Copy this to .env and fill in your test credentials

ARANGO_DATABASE=your_test_database
ARANGO_USER=root
ARANGO_PASSWORD=your_test_password
ARANGO_ENDPOINT=https://your-test-cluster.arangodb.cloud:8529

GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_api_key_secret

LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-flash-1.5-8b
```

**Customer project** (`~/code/your-customer-project/.env.example`):

```bash
# Copy this to .env and fill in production credentials

ARANGO_DATABASE=your_production_database
ARANGO_USER=root
ARANGO_PASSWORD=your_production_password
ARANGO_ENDPOINT=https://your-production-cluster.arangodb.cloud:8529

GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_production_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_production_api_key_secret

LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-flash-1.5-8b
```

---

## Quick Commands

```bash
# Swap credentials from library to customer project

# 1. Backup current (production) credentials
cd ~/code/graph-analytics-ai-platform
cp .env .env.production.backup

# 2. Copy production credentials to customer project
cp .env ~/code/your-customer-project/.env

# 3. Restore test credentials in library project
cat > .env << 'EOF'
ARANGO_DATABASE=graph-analytics-ai
ARANGO_USER=root
ARANGO_PASSWORD=your_test_password
ARANGO_ENDPOINT=https://your-test-cluster.arangodb.cloud:8529

GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your_test_api_key_id
ARANGO_GRAPH_API_KEY_SECRET=your_test_api_key_secret

LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-flash-1.5-8b

ARANGO_VERIFY_SSL=true
ARANGO_TIMEOUT=30
LOG_LEVEL=INFO
EOF
```

---

## Testing Each Project

### Test Library Project (with test credentials)

```bash
cd ~/code/graph-analytics-ai-platform

# Verify test database connection
python -c "from graph_analytics_ai.db_connection import get_db_connection; \
           db = get_db_connection(); \
           print(f'✅ Connected to: {db.name}')"

# Should output: ✅ Connected to: graph-analytics-ai

# Run library tests
pytest tests/ -v

# Run example workflow
python run_agentic_workflow.py
```

### Test Customer Project (with production credentials)

```bash
cd ~/code/your-customer-project

# Verify production database connection
python -c "from graph_analytics_ai.db_connection import get_db_connection; \
           db = get_db_connection(); \
           print(f'✅ Connected to: {db.name}')"

# Should output: ✅ Connected to: your_production_database

# Run customer workflow
python scripts/run_analysis.py
```

---

## Why This Separation?

### Library Project (Test Credentials)
✅ **Safe testing** - Won't affect production data  
✅ **Development** - Can modify library without risk  
✅ **CI/CD** - Can run tests in pipeline  
✅ **Multiple developers** - Each has own test environment  

### Customer Project (Production Credentials)
✅ **Production access** - Real customer data  
✅ **Isolated** - Credentials separate from library  
✅ **Secure** - Production credentials not in library repo  
✅ **Customer-specific** - Each customer has own credentials  

---

## Security Best Practices

1. ✅ **Never commit .env files** - Already in .gitignore
2. ✅ **Use .env.example** - Template without real credentials
3. ✅ **Separate credentials** - Library vs customer projects
4. ✅ **Rotate keys regularly** - Update production credentials periodically
5. ✅ **Limit access** - Only authorized users have production credentials

---

## Verification Checklist

After setting up both .env files:

### Library Project
- [ ] .env contains test database credentials
- [ ] Can connect to test database
- [ ] Tests run successfully
- [ ] Example scripts work

### Customer Project
- [ ] .env contains production credentials
- [ ] Can connect to production database
- [ ] Can import graph_analytics_ai library
- [ ] Workflow scripts work

---

## Troubleshooting

### Wrong Database Connected
```bash
# Check which database you're connecting to
python -c "from graph_analytics_ai.db_connection import get_db_connection; \
           db = get_db_connection(); print(db.name)"

# Library project should show: graph-analytics-ai
# Customer project should show: your_production_database
```

### Environment Variables Not Loading
```bash
# Check if .env file exists
ls -la .env

# Verify environment loading
python -c "import os; from dotenv import load_dotenv; \
           load_dotenv(); \
           print(f'Database: {os.getenv(\"ARANGO_DATABASE\")}')"
```

### Wrong Directory
```bash
# Always check your current directory
pwd

# Should be one of:
# /Users/arthurkeen/code/graph-analytics-ai-platform  (library)
# /Users/arthurkeen/code/your-customer-project         (customer)
```

---

## Summary

**Credential separation is essential!** You need to:

1. ✅ Move production credentials → `your-customer-project/.env`
2. ✅ Restore test credentials → `graph-analytics-ai-platform/.env`
3. ✅ Test library with test database
4. ✅ Test customer project with production database

This ensures:
- Library development doesn't affect production
- Customer project has correct production access
- Clear separation of concerns
- Better security posture

---

**Next Step:** Follow the commands above to swap the credentials, then test both projects!

