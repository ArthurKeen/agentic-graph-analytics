# Migration Guide: Adopting graph-analytics-ai Library

This guide provides step-by-step instructions for migrating each of the three source projects to use the common `graph-analytics-ai` library.

---

## Table of Contents

1. [General Migration Steps](#general-migration-steps)
2. [dnb_er Migration](#dnb_er-migration)
3. [matpriskollen Migration](#matpriskollen-migration)
4. [psi-graph-analytics Migration](#psi-graph-analytics-migration)
5. [Troubleshooting](#troubleshooting)

---

## General Migration Steps

### Step 1: Install the Library

```bash
# Option 1: Install from local source (during development)
cd /path/to/graph-analytics-ai
pip install -e .

# Option 2: Install from GitHub (once published)
pip install git+https://github.com/yourusername/graph-analytics-ai.git

# Option 3: Add to requirements.txt
echo "graph-analytics-ai>=1.0.0" >> requirements.txt
pip install -r requirements.txt
```

### Step 2: Update Environment Variables

Copy the `.env.example` from the library and update with your project's credentials:

```bash
cp /path/to/graph-analytics-ai/.env.example .env
# Edit .env with your credentials
```

**Key variables to set:**
- `GAE_DEPLOYMENT_MODE` - Set to `amp` or `self_managed` based on your deployment
- All ArangoDB connection variables
- GAE-specific credentials (if using AMP)

### Step 3: Update Imports

Replace project-specific imports with library imports:

**Before:**
```python
from scripts.gae_connection import GAEManager
from scripts.gae_orchestrator import GAEOrchestrator, AnalysisConfig
from scripts.db_connection import get_db_connection
from scripts.config import get_arango_config
```

**After:**
```python
from graph_analytics_ai import (
    GAEOrchestrator,
    AnalysisConfig,
    get_db_connection,
    get_arango_config
)
```

### Step 4: Update Code

Replace project-specific code with library equivalents. See project-specific sections below.

---

## dnb_er Migration

### Current State

- **Deployment:** AMP (Arango Managed Platform)
- **GAE Usage:** Currently minimal (mentioned in docs as future work)
- **Location:** `~/code/dnb_er`

### Migration Steps

#### 1. Install Library

```bash
cd ~/code/dnb_er
pip install -e /path/to/graph-analytics-ai
```

#### 2. Update .env File

Add GAE configuration to existing `.env`:

```bash
# Add to existing .env file
GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=your-key-id
ARANGO_GRAPH_API_KEY_SECRET=your-key-secret
ARANGO_GAE_PORT=8829
```

#### 3. Create GAE Analysis Script

Create a new script for GAE-based entity resolution:

```python
# scripts/run_gae_er.py
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

def run_wcc_entity_resolution():
    """Run WCC algorithm for entity resolution."""
    
    config = AnalysisConfig(
        name="entity_resolution_wcc",
        description="Weakly Connected Components for entity resolution",
        vertex_collections=["duns", "regs", "dbanames"],
        edge_collections=["similarity_edges", "cluster_edges"],
        algorithm="wcc",
        engine_size="e16",
        target_collection="entities"
    )
    
    orchestrator = GAEOrchestrator()
    result = orchestrator.run_analysis(config)
    
    return result

if __name__ == "__main__":
    result = run_wcc_entity_resolution()
    print(f"Analysis completed: {result.status}")
    print(f"Documents updated: {result.documents_updated}")
```

#### 4. Update Existing Code (if any)

If you have any existing GAE code, replace it with library calls:

**Before:**
```python
# Any custom GAE code
```

**After:**
```python
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig
# Use library
```

#### 5. Test Migration

```bash
# Test connection
python -c "from graph_analytics_ai import get_db_connection; get_db_connection()"

# Test GAE (if configured)
python scripts/run_gae_er.py
```

### Notes

- dnb_er currently has minimal GAE usage, so migration is straightforward
- Focus on adding new GAE-based entity resolution workflows
- Keep existing Python-based ER code as fallback

---

## matpriskollen Migration

### Current State

- **Deployment:** AMP (Arango Managed Platform)
- **GAE Usage:** Extensive - full orchestration system
- **Location:** `~/code/matpriskollen`
- **Key Files:**
  - `scripts/gae_connection.py`
  - `scripts/gae_orchestrator.py`
  - `scripts/config.py`
  - `scripts/db_connection.py`

### Migration Steps

#### 1. Install Library

```bash
cd ~/code/matpriskollen
pip install -e /path/to/graph-analytics-ai
```

#### 2. Backup Existing Code

```bash
# Create backup directory
mkdir -p scripts/backup
cp scripts/gae_connection.py scripts/backup/
cp scripts/gae_orchestrator.py scripts/backup/
cp scripts/config.py scripts/backup/
cp scripts/db_connection.py scripts/backup/
```

#### 3. Update .env File

Ensure `.env` has all required variables:

```bash
# ArangoDB connection (already exists)
ARANGO_ENDPOINT=...
ARANGO_USER=...
ARANGO_PASSWORD=...
ARANGO_DATABASE=mpk-analytic

# GAE configuration (add if missing)
GAE_DEPLOYMENT_MODE=amp
ARANGO_GRAPH_API_KEY_ID=...
ARANGO_GRAPH_API_KEY_SECRET=...
ARANGO_GAE_PORT=8829
```

#### 4. Update Imports in Scripts

**Update `scripts/run_analysis.py`:**

```python
# Before
from scripts.gae_orchestrator import GAEOrchestrator, AnalysisConfig
from scripts.db_connection import get_db_connection

# After
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig, get_db_connection
```

**Update `scripts/analysis_templates.py`:**

```python
# Before
from scripts.gae_orchestrator import AnalysisConfig

# After
from graph_analytics_ai import AnalysisConfig
```

#### 5. Update config.py (if needed)

Keep `scripts/config.py` for project-specific configuration, but remove GAE/ArangoDB connection code:

```python
# scripts/config.py - Keep only project-specific config
# Remove: get_arango_config, get_gae_config, get_db_connection
# Keep: Project-specific constants, analysis templates, etc.
```

#### 6. Remove Redundant Files (Optional)

After verifying everything works, you can remove the old files:

```bash
# Only after thorough testing!
rm scripts/gae_connection.py
rm scripts/gae_orchestrator.py
# Keep config.py and db_connection.py if they have project-specific code
```

#### 7. Update Tests

Update test files to use library imports:

```python
# tests/test_gae_connection.py
# Before
from scripts.gae_connection import GAEManager

# After
from graph_analytics_ai import GAEManager
```

#### 8. Test Migration

```bash
# Run existing tests
pytest tests/

# Test analysis templates
python scripts/run_analysis.py shop_distribution

# Verify cost tracking still works
python scripts/run_analysis.py user_product_journey
```

### Notes

- matpriskollen has the most extensive GAE usage
- Test all analysis templates after migration
- Verify cost tracking still works correctly
- Keep `analysis_templates.py` as it contains project-specific templates

---

## psi-graph-analytics Migration

### Current State

- **Deployment:** Self-managed (GenAI Platform)
- **GAE Usage:** Moderate - connection and basic orchestration
- **Location:** `~/code/psi-graph-analytics`
- **Key Files:**
  - `scripts/genai_gae_connection.py`
  - `scripts/db_connection.py`

### Migration Steps

#### 1. Install Library

```bash
cd ~/code/psi-graph-analytics
pip install -e /path/to/graph-analytics-ai
```

#### 2. Update .env File

Ensure `.env` has correct deployment mode:

```bash
# ArangoDB connection (already exists)
ARANGO_ENDPOINT=https://your-endpoint:8529
ARANGO_USER=root
ARANGO_PASSWORD=...
ARANGO_DATABASE=restore
ARANGO_VERIFY_SSL=false

# GAE configuration (add)
GAE_DEPLOYMENT_MODE=self_managed
# No additional GAE credentials needed for self-managed
```

#### 3. Update Imports

**Update example scripts:**

```python
# examples/run_full_network_pagerank.py
# Before
from scripts.genai_gae_connection import GenAIGAEConnection

# After
from graph_analytics_ai import GenAIGAEConnection, GAEOrchestrator, AnalysisConfig
```

#### 4. Migrate to Orchestrator (Recommended)

Replace manual workflow with orchestrator:

**Before:**
```python
from scripts.genai_gae_connection import GenAIGAEConnection

gae = GenAIGAEConnection()
gae.start_engine()
load_job = gae.load_graph(...)
gae.wait_for_job(load_job['id'])
pr_job = gae.run_pagerank(...)
gae.wait_for_job(pr_job['id'])
gae.store_results(...)
gae.stop_engine()
```

**After:**
```python
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

config = AnalysisConfig(
    name="investigator_pagerank",
    vertex_collections=["persons"],
    edge_collections=["investigator_connections"],
    algorithm="pagerank",
    target_collection="persons"
)

orchestrator = GAEOrchestrator()
result = orchestrator.run_analysis(config)
```

#### 5. Update Example Scripts

Update all example scripts in `examples/`:

```python
# examples/run_full_network_pagerank.py
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

def run_pagerank_analysis():
    config = AnalysisConfig(
        name="investigator_pagerank",
        description="PageRank analysis of investigator network",
        vertex_collections=["persons"],
        edge_collections=["investigator_connections"],
        algorithm="pagerank",
        algorithm_params={
            "damping_factor": 0.85,
            "maximum_supersteps": 100
        },
        target_collection="persons",
        result_field="pagerank_score"
    )
    
    orchestrator = GAEOrchestrator()
    result = orchestrator.run_analysis(config)
    
    print(f"Analysis completed: {result.status}")
    print(f"Documents updated: {result.documents_updated}")
    
    return result

if __name__ == "__main__":
    run_pagerank_analysis()
```

#### 6. Remove Redundant Files (Optional)

After verifying everything works:

```bash
# Only after thorough testing!
rm scripts/genai_gae_connection.py
# Keep db_connection.py if it has project-specific code
```

#### 7. Test Migration

```bash
# Test connection
python -c "from graph_analytics_ai import get_db_connection; get_db_connection()"

# Test GAE connection
python -c "from graph_analytics_ai import get_gae_connection; gae = get_gae_connection(); print('Connection OK')"

# Test example script
python examples/run_full_network_pagerank.py
```

### Notes

- psi-graph-analytics uses self-managed deployment
- No cost tracking (on-premises)
- Engine size parameter is ignored (managed by platform)
- JWT token authentication is handled automatically

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Error:** `ModuleNotFoundError: No module named 'graph_analytics_ai'`

**Solution:**
```bash
# Install library
pip install -e /path/to/graph-analytics-ai

# Or add to PYTHONPATH
export PYTHONPATH=/path/to/graph-analytics-ai:$PYTHONPATH
```

#### 2. Configuration Errors

**Error:** `Missing required environment variables`

**Solution:**
- Check `.env` file exists and has all required variables
- Verify `GAE_DEPLOYMENT_MODE` is set correctly (`amp` or `self_managed`)
- For AMP: Ensure API keys are set
- For self-managed: Ensure ArangoDB credentials are set

#### 3. Token Errors (AMP)

**Error:** `ARANGO_GRAPH_TOKEN not set` or `401 Unauthorized`

**Solution:**
```bash
# Generate token using oasisctl
oasisctl login --key-id $ARANGO_GRAPH_API_KEY_ID --key-secret $ARANGO_GRAPH_API_KEY_SECRET

# Or set in .env
ARANGO_GRAPH_TOKEN=$(oasisctl login --key-id ... --key-secret ...)
```

#### 4. Connection Errors (Self-Managed)

**Error:** `401 Unauthorized` or `Failed to get JWT token`

**Solution:**
- Verify ArangoDB credentials in `.env`
- Check endpoint URL includes port (`:8529`) - **This is the #1 cause of 401 errors!**
- Verify SSL settings (`ARANGO_VERIFY_SSL=false` for self-signed certs)
- Check network/VPN access
- Check for password formatting issues (extra spaces)

**Enhanced Error Messages:**
The library now includes enhanced error messages based on customer experience (Dima's issues):

1. **Missing Port Detection:**
   - Automatically detects if endpoint is missing `:8529`
   - Warns during initialization
   - Provides clear fix instructions

2. **Password Formatting Checks:**
   - Detects leading/trailing spaces
   - Warns about quoted passwords
   - Provides specific fix instructions

3. **Authorization Error Details:**
   - Explains common causes (limited users, wrong credentials, etc.)
   - Provides step-by-step troubleshooting
   - Suggests specific fixes

4. **Limited User Support:**
   - Handles users without `_system` database access
   - Gracefully falls back to direct database connection
   - Provides clear warnings about permission limitations

**Use Validation Utility:**
```python
from graph_analytics_ai import get_credential_validation_report

# Check credentials before connecting
report = get_credential_validation_report()
print(report)
```

#### 5. Algorithm Not Supported

**Error:** `Unsupported algorithm: betweenness`

**Solution:**
- Betweenness centrality is not yet implemented in the base connection classes
- Use supported algorithms: `pagerank`, `wcc`, `scc`, `label_propagation`
- Or implement custom algorithm method

### Getting Help

1. Check library documentation: `README.md`
2. Review PRD: `PRD.md`
3. Check example code in source projects
4. Review error messages and logs

---

## Migration Checklist

### Pre-Migration

- [ ] Backup existing code
- [ ] Review current GAE usage in project
- [ ] Identify all files that need updating
- [ ] Document project-specific configurations

### Migration

- [ ] Install library
- [ ] Update `.env` file
- [ ] Update imports in all files
- [ ] Replace custom code with library calls
- [ ] Update tests
- [ ] Update documentation

### Post-Migration

- [ ] Run all tests
- [ ] Test all analysis workflows
- [ ] Verify cost tracking (AMP only)
- [ ] Update project documentation
- [ ] Remove redundant files (optional)
- [ ] Commit changes

---

## Next Steps

After successful migration:

1. **Update Documentation:** Update project README with new library usage
2. **Share Learnings:** Document any project-specific patterns or extensions
3. **Contribute:** Consider contributing improvements back to the library
4. **Monitor:** Monitor for any issues and report them

---

## Support

For issues or questions:

1. Check this migration guide
2. Review library documentation
3. Check source project examples
4. Open an issue on the library repository

