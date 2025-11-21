# Product Requirements Document (PRD): Graph Analytics AI Library

**Document Status:** Living Document  
**Last Updated:** December 2025  
**Version:** 1.1.0 (AI Workflow Added)  
**Purpose:** Common library for orchestrating ArangoDB Graph Analytics Engine (GAE) operations

---

## 1. Introduction and Goals

### 1.1 Project Overview

This library provides a unified interface for orchestrating ArangoDB Graph Analytics Engine (GAE) operations across multiple deployment models. It was extracted from three projects that had overlapping functionality:

1. **dnb_er** - Dun & Bradstreet Entity Resolution (AMP deployment)
2. **matpriskollen** - Consumer behavior analytics (AMP deployment)
3. **psi-graph-analytics** - CRO investigator network analysis (self-managed deployment)

### 1.2 Key Objectives

1. **Unified Interface:** Provide a single, consistent API for GAE operations regardless of deployment model
2. **Deployment Flexibility:** Support both Arango Managed Platform (AMP) and self-managed deployments
3. **Complete Workflow Automation:** Automate the full lifecycle of graph analytics operations
4. **AI-Assisted Workflow:** Enable customers to go from business requirements to actionable insights without manual intervention
5. **Cost Management:** Track and manage costs for cloud-based deployments
6. **Error Handling:** Robust error handling and retry logic for production use
7. **Code Reusability:** Eliminate duplicate code across projects
8. **LLM Agnostic:** Support any LLM provider through a unified interface

### 1.3 Core Requirements

- Support for multiple graph algorithms (PageRank, WCC, SCC, Label Propagation, Betweenness)
- Automatic engine lifecycle management (deploy, use, cleanup)
- Result storage and verification
- Cost tracking for AMP deployments
- Comprehensive error handling and retry logic
- Support for batch analysis workflows
- Configuration via environment variables (.env file)
- **AI-Assisted Workflow:** Automated end-to-end workflow from business requirements to actionable insights
  - Graph schema analysis and understanding
  - PRD generation from business requirements
  - Use case generation based on schema and requirements
  - Template generation for GAE analyses
  - Report generation with actionable intelligence
- **LLM Provider Agnostic:** Support for any LLM provider (OpenAI, Anthropic, custom APIs)

---

## 2. Deployment Models

### 2.1 Arango Managed Platform (AMP)

**Authentication:**
- Uses API keys (`ARANGO_GRAPH_API_KEY_ID`, `ARANGO_GRAPH_API_KEY_SECRET`)
- Generates access tokens via `oasisctl` CLI tool
- Tokens expire after 24 hours (automatic refresh supported)

**Engine Management:**
- Deploy engines via Management API
- Configurable engine sizes (e4, e8, e16, e32, e64, e128)
- Cost tracking based on engine size and runtime

**Projects Using AMP:**
- dnb_er
- matpriskollen

### 2.2 Self-Managed (GenAI Platform)

**Authentication:**
- Uses JWT tokens from ArangoDB (`/_open/auth` endpoint)
- Same credentials as ArangoDB connection
- Tokens obtained via standard ArangoDB authentication

**Engine Management:**
- Start engines via GenAI service API (`/gen-ai/v1/graphanalytics`)
- Engine size not configurable (managed by platform)
- No cost tracking (on-premises deployment)

**Projects Using Self-Managed:**
- psi-graph-analytics

---

## 3. Core Functionality

### 3.1 Graph Analytics Algorithms

The library supports the following algorithms:

| Algorithm | Use Case | Parameters |
|-----------|----------|------------|
| **PageRank** | Influence analysis, centrality | damping_factor, maximum_supersteps |
| **Weakly Connected Components (WCC)** | Community detection, data quality | None |
| **Strongly Connected Components (SCC)** | Cyclic relationships, temporal analysis | None |
| **Label Propagation** | Community detection, clustering | start_label_attribute, synchronous, random_tiebreak, maximum_supersteps |
| **Betweenness Centrality** | Bridge detection, critical paths | maximum_supersteps |

### 3.2 Workflow Orchestration

The orchestrator automates the complete workflow:

1. **Engine Deployment:** Deploy or start GAE engine
2. **Graph Loading:** Load graph data from ArangoDB collections
3. **Algorithm Execution:** Run the configured algorithm
4. **Result Storage:** Write results back to ArangoDB
5. **Cleanup:** Delete/stop engine to prevent orphaned resources

### 3.3 Error Handling

- **Retry Logic:** Automatic retry for transient errors
- **Non-Retryable Errors:** Configuration errors are not retried
- **Guaranteed Cleanup:** Engines are always cleaned up, even on failure
- **Safety Checks:** Warns about existing engines before deployment

### 3.4 Cost Management (AMP Only)

- Tracks engine runtime
- Calculates estimated costs based on engine size
- Provides cost estimates before analysis
- Logs cost information in analysis results

---

## 4. Configuration

### 4.1 Environment Variables

**Required for All Deployments:**
- `ARANGO_ENDPOINT` - ArangoDB endpoint URL
- `ARANGO_USER` - Database username
- `ARANGO_PASSWORD` - Database password
- `ARANGO_DATABASE` - Database name

**For AMP Deployments:**
- `GAE_DEPLOYMENT_MODE=amp`
- `ARANGO_GRAPH_API_KEY_ID` - API key ID
- `ARANGO_GRAPH_API_KEY_SECRET` - API key secret
- `ARANGO_GRAPH_TOKEN` - (Optional) Pre-generated token
- `ARANGO_GAE_PORT` - (Optional) GAE port (default: 8829)

**For Self-Managed Deployments:**
- `GAE_DEPLOYMENT_MODE=self_managed`
- No additional GAE credentials needed

### 4.2 Configuration File

Configuration is managed via `.env` file (see `.env.example` for template).

---

## 5. Usage Examples

### 5.1 Basic Analysis

```python
from graph_analytics_ai import GAEOrchestrator, AnalysisConfig

# Define analysis
config = AnalysisConfig(
    name="product_demand",
    vertex_collections=["users", "products"],
    edge_collections=["clicks"],
    algorithm="pagerank",
    engine_size="e16"
)

# Run analysis
orchestrator = GAEOrchestrator()
result = orchestrator.run_analysis(config)

# Check results
print(f"Status: {result.status}")
print(f"Documents updated: {result.documents_updated}")
print(f"Cost: ${result.estimated_cost_usd}")
```

### 5.2 Batch Analysis

```python
configs = [
    AnalysisConfig(name="analysis1", ...),
    AnalysisConfig(name="analysis2", ...),
]

results = orchestrator.run_batch(configs)
```

### 5.3 Custom Algorithm Parameters

```python
config = AnalysisConfig(
    name="community_detection",
    vertex_collections=["nodes"],
    edge_collections=["edges"],
    algorithm="label_propagation",
    algorithm_params={
        "start_label_attribute": "_key",
        "synchronous": False,
        "maximum_supersteps": 200
    }
)
```

---

## 6. Architecture

### 6.1 Component Structure

```
graph_analytics_ai/
├── __init__.py          # Public API
├── config.py            # Configuration management
├── db_connection.py     # ArangoDB connection
├── gae_connection.py    # GAE connection (AMP & self-managed)
├── gae_orchestrator.py  # Workflow orchestration
├── llm/                 # LLM provider abstraction (v2.0)
│   ├── base.py          # Base LLM provider interface
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   └── factory.py
├── schema/              # Schema analysis (v2.0)
│   ├── extractor.py     # Extract schema from ArangoDB
│   └── analyzer.py      # Analyze schema structure
├── prd/                 # PRD generation (v2.0)
│   ├── generator.py     # Generate PRDs
│   └── modifier.py      # Modify PRDs based on schema
├── usecases/            # Use case generation (v2.0)
│   └── generator.py     # Generate use cases
├── templates/           # Template generation (v2.0)
│   └── generator.py     # Generate GAE templates
├── reporting/           # Report generation (v2.0)
│   ├── generator.py     # Generate reports
│   └── interpreter.py   # Interpret results
└── workflow/            # Workflow orchestration (v2.0)
    ├── orchestrator.py  # Main workflow orchestrator
    └── steps.py         # Individual workflow steps
```

### 6.2 Connection Abstraction

The library uses a base class (`GAEConnectionBase`) with two implementations:
- `GAEManager` - For AMP deployments
- `GenAIGAEConnection` - For self-managed deployments

A factory function (`get_gae_connection()`) automatically selects the appropriate implementation based on configuration.

---

## 7. Success Criteria

### 7.1 Functional Requirements

-  Support both AMP and self-managed deployments
-  Automate complete workflow (deploy → load → analyze → store → cleanup)
-  Support all major graph algorithms
-  Handle errors gracefully with retry logic
-  Track costs for AMP deployments
-  Provide clear error messages and logging

### 7.2 Non-Functional Requirements

-  Configuration via environment variables
-  Comprehensive documentation
-  Migration guides for existing projects
-  Code reusability (single library for all projects)
-  Backward compatibility where possible

---

## 8. AI-Assisted Workflow Automation

### 8.1 Overview

The library provides an AI-assisted workflow that automates the complete process from business requirements to actionable graph analytics insights. This enables customers to leverage their own LLM providers to:

1. **Analyze Business Requirements** - Extract and structure business requirements from documents
2. **Understand Graph Schema** - Automatically analyze customer graph database structure
3. **Generate PRD** - Create Product Requirements Document from requirements and schema
4. **Create Use Cases** - Generate GAE analytics use cases with business context
5. **Generate Templates** - Create GAE analysis templates from use cases
6. **Execute Analyses** - Run analyses using existing GAE orchestration
7. **Generate Reports** - Create actionable intelligence reports from results

### 8.2 Workflow Steps

#### Step 1: Domain Analysis / Business Requirements
- **Input:** Business requirements documents, use case notes, domain knowledge
- **Process:** LLM analyzes and structures requirements
- **Output:** Structured business requirements document

#### Step 2: Graph Schema Analysis
- **Input:** ArangoDB database connection
- **Process:** 
  - Extract collection structure (vertices and edges)
  - Analyze relationships and patterns
  - Identify key entities and attributes
- **Output:** Graph schema analysis document

#### Step 3: PRD Generation
- **Input:** Business requirements + Graph schema
- **Process:** LLM generates comprehensive PRD incorporating:
  - Business objectives
  - Graph structure insights
  - Technical constraints
  - Success criteria
- **Output:** Complete Product Requirements Document

#### Step 4: Use Case Generation
- **Input:** PRD + Graph schema
- **Process:** LLM generates analytics use cases:
  - Maps business requirements to graph algorithms
  - Identifies relevant collections and relationships
  - Explains business value and expected outcomes
- **Output:** List of analytics use cases with descriptions

#### Step 5: Template Generation
- **Input:** Use cases + Graph schema
- **Process:** 
  - Converts use cases to `AnalysisConfig` objects
  - Sets optimal algorithm parameters
  - Configures engine sizes based on graph size
- **Output:** GAE analysis templates ready for execution

#### Step 6: Analysis Execution
- **Input:** Analysis templates
- **Process:** Uses existing `GAEOrchestrator` to execute analyses
- **Output:** Analysis results with metrics and data

#### Step 7: Report Generation
- **Input:** Analysis results + Original requirements
- **Process:** LLM generates comprehensive report:
  - Summarizes findings
  - Interprets results in business context
  - Provides actionable recommendations
  - Explains insights and implications
- **Output:** Actionable intelligence report

### 8.3 LLM Provider Support

The library is **LLM-agnostic** and supports:

- **OpenAI** (GPT-4, GPT-3.5, GPT-4 Turbo)
- **Anthropic** (Claude 3, Claude 2)
- **Generic REST API** - Any LLM provider with REST API
- **Custom Providers** - Extensible interface for custom implementations

Customers provide their own LLM API keys and configuration.

### 8.4 Configuration

**LLM Configuration:**
```bash
# LLM Provider Selection
LLM_PROVIDER=openai  # openai, anthropic, generic
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4  # Model name (provider-specific)
LLM_BASE_URL=  # For generic provider
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.7

# Workflow Configuration
WORKFLOW_OUTPUT_DIR=./workflow_output
WORKFLOW_CHECKPOINT_ENABLED=true
```

### 8.5 Usage Example

```python
from graph_analytics_ai.workflow import AIWorkflowOrchestrator

# Initialize AI workflow
workflow = AIWorkflowOrchestrator(
    llm_provider="openai",
    llm_api_key=os.getenv("LLM_API_KEY"),
    output_dir="./workflow_output"
)

# Run complete workflow
result = workflow.run_complete_workflow(
    business_requirements="path/to/requirements.md",
    database_name="customer_db"
)

# Or run individual steps
schema = workflow.analyze_schema(database_name="customer_db")
prd = workflow.generate_prd(business_requirements="path/to/requirements.md")
use_cases = workflow.generate_use_cases(prd=prd, schema=schema)
templates = workflow.generate_templates(use_cases=use_cases)
results = workflow.run_analyses(templates=templates)
report = workflow.generate_report(results=results, requirements="path/to/requirements.md")
```

### 8.6 Architecture Components

The AI workflow consists of:

- **LLM Abstraction Layer** - Provider-agnostic LLM interface
- **Schema Analyzer** - Extract and analyze graph database schema
- **PRD Generator** - Generate PRDs from requirements and schema
- **Use Case Generator** - Create analytics use cases
- **Template Generator** - Generate GAE analysis templates
- **Report Generator** - Create actionable intelligence reports
- **Workflow Orchestrator** - Coordinate all workflow steps

### 8.7 Benefits

- **Reduced Time to Value:** From weeks to hours
- **No Manual Intervention:** Fully automated workflow
- **Consistent Quality:** Standardized process and outputs
- **Customer Control:** Use their own LLM and API keys
- **Scalable:** Works with any graph database and requirements

### 8.8 Agentic Workflow Option

The AI workflow can be implemented using either a **linear orchestrated approach** or an **agentic workflow approach**:

**Linear Orchestrated (v2.0.0):**
- Sequential step execution
- LLM prompts for decision-making
- Simpler implementation
- Predictable execution

**Agentic Workflow (v2.1.0+):**
- Autonomous agents for each domain
- Agents can reason and adapt
- Better decision-making
- Higher quality outputs
- More adaptive to edge cases

**Why Agentic?**
This project is an excellent candidate for agentic workflow because:
- Complex decision-making required (algorithm selection, optimization)
- Multiple domains of expertise (business, graph, analytics)
- Need for adaptive execution (handle unexpected situations)
- Quality assurance important (validation at each step)
- Explainability valuable (understand agent reasoning)

See `AGENTIC_WORKFLOW_ANALYSIS.md` for detailed analysis and architecture proposal.

---

## 9. Future Enhancements

### 9.1 Planned Features

- **Temporal Analysis:** Support for time-series graph analysis
- **Graph Filtering:** AQL-based filtering before graph loading
- **Additional Algorithms:** Betweenness centrality, additional community detection algorithms
- **Scheduling:** Support for scheduled analysis runs
- **Monitoring:** Integration with monitoring systems
- **Caching:** Result caching for repeated analyses
- **AI Workflow Enhancements:**
  - **Agentic Workflow:** Multi-agent system with autonomous decision-making (v2.1.0)
  - Multi-LLM support (use different LLMs for different tasks)
  - Learning system (improve prompts based on feedback)
  - Custom prompt templates
  - Integration with NotebookLM API
  - Interactive workflow mode

### 9.2 Integration Opportunities

- **Airflow:** Integration with Apache Airflow for workflow orchestration
- **Jupyter:** Notebook integration for interactive analysis
- **Dashboards:** Result visualization and dashboard integration
- **NotebookLM:** Direct integration with NotebookLM for domain analysis

---

## 10. Implementation Roadmap

### Phase 1: Foundation (v1.1.0) - Q1 2026
- LLM abstraction layer
- Basic schema analysis
- Configuration system for LLM providers

### Phase 2: PRD Generation (v1.2.0) - Q1 2026
- PRD generation from requirements
- PRD modification based on schema
- PRD templates

### Phase 3: Use Case Generation (v1.3.0) - Q2 2026
- Use case generation from PRD and schema
- Use case validation
- Business value explanation

### Phase 4: Template Generation (v1.4.0) - Q2 2026
- Template generation from use cases
- Template optimization
- Parameter tuning

### Phase 5: Report Generation (v1.5.0) - Q2 2026
- Report generation from results
- Result interpretation
- Multiple output formats

### Phase 6: Complete Workflow (v2.0.0) - Q3 2026
- End-to-end workflow orchestration (linear approach)
- CLI interface
- Interactive mode
- Checkpoint/resume functionality

### Phase 7: Agentic Workflow (v2.1.0) - Q4 2026
- Agentic workflow implementation
- Multi-agent architecture
- Autonomous decision-making
- Adaptive execution
- Agent collaboration

---

## 11. References

### 11.1 Source Projects

- **dnb_er:** Entity resolution for Dun & Bradstreet data
- **matpriskollen:** Consumer behavior analytics platform
- **psi-graph-analytics:** CRO investigator network analysis

### 11.2 Documentation

- ArangoDB Graph Analytics Engine: https://docs.arangodb.com/stable/arangograph/graph-analytics/
- ArangoDB Python Driver: https://python-arango.readthedocs.io/
- Oasisctl CLI: https://github.com/arangodb-managed/oasisctl
- AI Workflow Implementation Plan: See `AI_WORKFLOW_PLAN.md`

---

## 12. Version History

### Version 2.0.0 (Planned - Q3 2026)
- Complete AI-assisted workflow automation
- LLM provider abstraction
- End-to-end workflow orchestration
- CLI interface

### Version 1.0.0 (December 2025)

- Initial release
- Support for AMP and self-managed deployments
- Complete workflow orchestration
- Cost tracking for AMP
- Comprehensive error handling
- Migration guides for source projects

