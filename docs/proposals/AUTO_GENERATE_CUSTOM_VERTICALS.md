# Plan: Auto-Generate Custom Industry Verticals from Business Requirements

## Executive Summary

Enable the agentic workflow to automatically detect when no matching industry vertical exists and generate a custom vertical from the provided business requirements document. The custom vertical is stored in the client project and can be reused across runs.

---

## Problem Statement

**Current State:**
- Platform has 5 built-in verticals (adtech, fintech, fraud_intelligence, social, generic)
- If your domain doesn't match, you get `generic` analysis (suboptimal)
- Adding new verticals requires code changes to the platform

**Desired State:**
- Submit business requirements for any domain
- Platform auto-generates domain-specific prompts and patterns
- Custom vertical stored in client project for reuse
- No platform code changes needed

---

## Architecture Design

### High-Level Flow

```mermaid
flowchart TD
  A["1. Run workflow<br/>industry = 'auto' or unknown"] --> B["2. Check client project for custom vertical<br/>.graph-analytics/industry_vertical.json"]
  B --> C{Found?}

  C -- Yes --> D["Load custom vertical and use"]
  C -- No --> E["Check business requirements doc(s)"]
  E --> F["IndustryVertical Generation Agent<br/>- Analyze domain<br/>- Extract entities<br/>- Identify patterns<br/>- Generate prompt"]
  F --> G["Save to client project<br/>.graph-analytics/industry_vertical.json"]
  G --> H["Use generated vertical for analysis"]

  D --> H
```

---

## Component Design

### 1. Industry Vertical Schema

**File:** `.graph-analytics/industry_vertical.json` (in client project)

```json
{
  "metadata": {
    "name": "supply_chain",
    "display_name": "Supply Chain & Logistics",
    "version": "1.0",
    "generated_at": "2026-02-10T10:30:00Z",
    "generated_by": "IndustryVerticalAgent",
    "source_documents": [
      "docs/business_requirements.md",
      "docs/domain_description.md"
    ]
  },
  "domain_context": {
    "industry": "Supply Chain & Logistics",
    "business_focus": "Optimize supply chain resilience, detect bottlenecks, predict disruptions",
    "key_entities": {
      "nodes": [
        "Supplier: Manufacturing suppliers and vendors",
        "Warehouse: Distribution centers and storage facilities",
        "Product: SKUs and inventory items",
        "ShipmentRoute: Transportation corridors",
        "Port: Import/export facilities"
      ],
      "edges": [
        "suppliesTo: Supply relationships between entities",
        "shipsVia: Transportation routes",
        "stores: Inventory storage relationships",
        "dependsOn: Supply dependencies"
      ]
    },
    "key_metrics": [
      "Lead time variance",
      "Inventory turnover",
      "Supply chain resilience score",
      "Bottleneck detection",
      "Geographic concentration risk"
    ],
    "terminology": {
      "currency": "USD",
      "units": ["units", "pallets", "containers", "days"],
      "regulations": ["Import/Export regulations", "Customs compliance"],
      "thresholds": {
        "critical_inventory": "< 7 days",
        "single_supplier_risk": "> 30% of volume"
      }
    }
  },
  "analysis_prompt": "You are analyzing a supply chain and logistics graph...\n\n[Full LLM prompt here]",
  "pattern_definitions": {
    "wcc": [
      {
        "name": "single_point_of_failure",
        "description": "Critical supplier with no alternatives",
        "indicators": ["Single supplier for key component", "No backup in same region"],
        "risk_level": "CRITICAL",
        "example": "Supplier S-123 is sole provider of Component X (40% of product line)"
      },
      {
        "name": "geographic_concentration",
        "description": "Over-reliance on single geographic region",
        "indicators": [">50% suppliers in one region", "Geopolitical risk exposure"],
        "risk_level": "HIGH"
      }
    ],
    "pagerank": [
      {
        "name": "critical_hub",
        "description": "Warehouse or supplier that many others depend on",
        "indicators": ["High centrality", ">20 downstream dependencies"],
        "risk_level": "HIGH"
      }
    ]
  },
  "user_validated": false,
  "user_notes": ""
}
```

### 2. IndustryVerticalAgent (New Agent)

**Location:** `graph_analytics_ai/ai/agents/industry_vertical.py`

**Purpose:** Analyze business requirements and generate custom industry vertical

**Inputs:**
- Business requirements document(s)
- Domain description (optional)
- Schema information from database

**Outputs:**
- Industry vertical JSON file
- Validation report

**Capabilities:**
```python
class IndustryVerticalAgent:
    """
    Agent that generates custom industry verticals from business requirements.
    
    This agent:
    1. Analyzes business requirements to understand the domain
    2. Identifies key entities (nodes/edges) from the graph schema
    3. Extracts domain-specific terminology and metrics
    4. Generates an LLM prompt tailored to the industry
    5. Defines pattern templates for common algorithms
    """
    
    async def analyze_domain(
        self,
        business_requirements: str,
        domain_description: Optional[str],
        graph_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze domain and extract key characteristics."""
        
    async def generate_prompt(
        self,
        domain_analysis: Dict[str, Any]
    ) -> str:
        """Generate industry-specific LLM prompt."""
        
    async def generate_pattern_definitions(
        self,
        domain_analysis: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate pattern definitions for WCC, PageRank, etc."""
        
    async def save_vertical(
        self,
        vertical: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Save generated vertical to client project."""
```

### 3. Custom Vertical Loader

**Location:** `graph_analytics_ai/ai/reporting/custom_prompts.py`

```python
def load_custom_vertical(project_root: Path) -> Optional[Dict[str, Any]]:
    """
    Load custom industry vertical from client project.
    
    Looks for: <project_root>/.graph-analytics/industry_vertical.json
    """
    vertical_path = project_root / ".graph-analytics" / "industry_vertical.json"
    if vertical_path.exists():
        return json.loads(vertical_path.read_text())
    return None

def register_custom_vertical(vertical: Dict[str, Any]) -> str:
    """
    Register custom vertical with the platform for current session.
    
    Returns the industry key to use.
    """
    industry_key = vertical["metadata"]["name"]
    prompt = vertical["analysis_prompt"]
    
    # Register in the global registry
    from graph_analytics_ai.ai.reporting.prompts import INDUSTRY_PROMPTS
    INDUSTRY_PROMPTS[industry_key] = prompt
    
    return industry_key
```

### 4. Modified Workflow Orchestrator

**Location:** `graph_analytics_ai/ai/agents/orchestrator.py`

**Changes:**

```python
async def run_workflow_async(
    self,
    input_documents: List[str],
    database_config: Optional[Dict],
    enable_parallelism: bool = True,
    industry: str = "generic",  # Can now be "auto"
    auto_generate_vertical: bool = True,  # New parameter
) -> WorkflowState:
    """Run the complete agentic workflow."""
    
    # NEW: Auto-detect and generate custom vertical
    if industry == "auto" or (auto_generate_vertical and not self._is_known_industry(industry)):
        print(f"Industry '{industry}' not found in built-in verticals.")
        print("Checking for custom vertical in project...")
        
        # Try to load existing custom vertical
        custom_vertical = load_custom_vertical(Path.cwd())
        
        if custom_vertical:
            print(f"✓ Found custom vertical: {custom_vertical['metadata']['display_name']}")
            industry = register_custom_vertical(custom_vertical)
        else:
            print("No custom vertical found. Generating from business requirements...")
            
            # Generate new vertical
            vertical_agent = IndustryVerticalAgent(llm_provider=self.llm_provider)
            
            # Load business requirements
            business_reqs = self._load_input_documents(input_documents)
            
            # Analyze and generate
            vertical = await vertical_agent.generate_vertical(
                business_requirements=business_reqs,
                graph_name=self.graph_name,
                graph_connection=self.graph_connection
            )
            
            # Save to project
            output_path = Path.cwd() / ".graph-analytics" / "industry_vertical.json"
            output_path.parent.mkdir(exist_ok=True)
            await vertical_agent.save_vertical(vertical, output_path)
            
            print(f"✓ Generated custom vertical: {vertical['metadata']['display_name']}")
            print(f"✓ Saved to: {output_path}")
            
            # Register for this run
            industry = register_custom_vertical(vertical)
    
    # Continue with normal workflow using the industry
    # ...
```

---

## Business Requirements Document Guidelines

### Current Guidelines Are Good, But Add These Sections:

**Add to business requirements template:**

```markdown
# Business Requirements Document

## 1. Domain Overview (NEW - REQUIRED for auto-generation)

**Industry/Vertical:** [e.g., Supply Chain, Healthcare, Cybersecurity]

**Primary Business Function:** [e.g., Optimize logistics, Detect fraud, Track disease spread]

**Target Users:** [e.g., Supply chain analysts, Risk managers, Epidemiologists]

## 2. Domain Terminology (NEW - REQUIRED)

**Currency/Units:**
- Primary currency: [e.g., USD, EUR, ₹ Crores]
- Measurement units: [e.g., units, transactions, patients, devices]

**Key Terms:**
- [Term 1]: [Definition]
- [Term 2]: [Definition]

**Regulatory/Compliance Context:**
- [Regulation 1]: [Brief description]
- [Regulation 2]: [Brief description]

**Thresholds/Benchmarks:**
- [Threshold 1]: [Value and meaning]
- [Threshold 2]: [Value and meaning]

## 3. Graph Structure (Enhance existing section)

**Node Types:**
For each node type, specify:
- Name
- Business meaning
- Example attributes
- Typical volume

**Edge Types:**
For each edge type, specify:
- Name
- Business meaning
- Direction (directed/undirected)
- Typical patterns

## 4. Key Metrics & KPIs (NEW - REQUIRED)

What metrics define success in this domain?
- [Metric 1]: [Definition, normal range, critical threshold]
- [Metric 2]: [Definition, normal range, critical threshold]

## 5. Patterns to Detect (Enhance existing section)

**Critical Patterns:** (What's bad/risky?)
- [Pattern 1]: [Description, indicators, business impact]

**Valuable Patterns:** (What's good/opportunity?)
- [Pattern 1]: [Description, indicators, business value]

**Anomalies:** (What's unusual?)
- [Pattern 1]: [Description, what makes it anomalous]

## 6. Risk Classification (NEW - OPTIONAL)

How should findings be classified?
- **CRITICAL:** [Definition, examples]
- **HIGH:** [Definition, examples]
- **MEDIUM:** [Definition, examples]
- **LOW:** [Definition, examples]

## 7. Action Framework (NEW - OPTIONAL)

What actions should analysts take based on findings?

**Immediate Actions (0-24 hours):**
- [Action type]: [When to use, who to notify]

**Short-term Actions (1-7 days):**
- [Action type]: [When to use, process]

**Long-term Actions (Strategic):**
- [Action type]: [When to use, planning]

## 8. Example Insights (NEW - RECOMMENDED)

Provide 2-3 examples of ideal insights for this domain:

**Good Insight Example:**
```
Title: [Specific, quantified finding]
Description: [Detailed analysis with domain context and numbers]
Business Impact: [Specific actions, financial impact, urgency]
Confidence: [0.7-0.95]
```

**Bad Insight Example:**
```
Title: [Generic, vague finding]
Why it's bad: [Missing specifics, no context, unclear action]
```

## 9. Success Criteria (Existing - keep as is)

[How to measure if analysis is successful]
```

### Template Location

Create: `agentic-graph-analytics/templates/business_requirements_template.md`

---

## Storage Strategy

### Option 1: Client Project Storage (RECOMMENDED)

**Location:** `<client-project>/.graph-analytics/industry_vertical.json`

**Pros:**
- Custom verticals stay with the project
- Easy to version control with project
- No platform modifications needed
- Each project can have unique vertical
- Can be committed to client repo

**Cons:**
- Not shareable across projects without copying
- Each project regenerates if starting fresh

**Implementation:**
```
fraud-intelligence/
  .graph-analytics/
    industry_vertical.json      ← Generated custom vertical
    vertical_generation.log     ← Generation log
    user_notes.md              ← User refinements
  docs/
    business_requirements.md
    domain_description.md
  ...
```

### Option 2: Platform Registry (For sharing)

**Location:** `agentic-graph-analytics/graph_analytics_ai/ai/reporting/custom_verticals/`

**Use case:** When multiple projects use the same custom vertical

```
agentic-graph-analytics/
  graph_analytics_ai/
    ai/
      reporting/
        custom_verticals/
          supply_chain.json
          healthcare.json
          cybersecurity.json
```

### Option 3: Hybrid Approach (BEST)

**Strategy:**
1. Generate and store in client project (`.graph-analytics/`)
2. Provide command to "promote" vertical to platform registry
3. Load order: client project → platform custom → built-in

```python
# Load priority
def get_industry_prompt(industry: str, project_root: Path) -> str:
    # 1. Try client project custom vertical
    custom = load_custom_vertical(project_root)
    if custom and custom["metadata"]["name"] == industry:
        return custom["analysis_prompt"]
    
    # 2. Try platform custom verticals
    platform_custom = load_platform_custom_vertical(industry)
    if platform_custom:
        return platform_custom["analysis_prompt"]
    
    # 3. Fall back to built-in
    return INDUSTRY_PROMPTS.get(industry, GENERIC_PROMPT)
```

---

## Workflow Integration

### Phase 1: Detection & Generation

**When workflow starts:**

```python
# 1. User provides industry parameter
runner = AgenticWorkflowRunner(
    graph_name="my_supply_chain",
    industry="auto",  # NEW: triggers auto-detection
    # OR
    industry="supply_chain"  # Unknown vertical also triggers
)

# 2. Workflow checks
if industry not in KNOWN_INDUSTRIES:
    # Check for custom vertical in project
    custom_vertical_path = Path.cwd() / ".graph-analytics/industry_vertical.json"
    
    if custom_vertical_path.exists():
        # Load and use existing
        vertical = load_custom_vertical(Path.cwd())
        industry_key = register_custom_vertical(vertical)
    else:
        # Generate new
        print("Generating custom industry vertical from business requirements...")
        vertical = await IndustryVerticalAgent().generate_vertical(
            business_requirements="docs/business_requirements.md",
            graph_name="my_supply_chain"
        )
        save_custom_vertical(vertical, custom_vertical_path)
        industry_key = register_custom_vertical(vertical)
```

### Phase 2: Validation & Refinement

**After generation, present to user:**

```
╔════════════════════════════════════════════════════════════════╗
║  Custom Industry Vertical Generated                           ║
╚════════════════════════════════════════════════════════════════╝

Industry: Supply Chain & Logistics
Entities: 5 node types, 4 edge types identified
Patterns: 6 pattern definitions created
Risk Levels: CRITICAL, HIGH, MEDIUM, LOW defined

Generated vertical saved to:
  .graph-analytics/industry_vertical.json

✓ Review the generated vertical
✓ Edit if needed (add terminology, refine patterns)
✓ Re-run workflow to use updated vertical

Commands:
  • View:   cat .graph-analytics/industry_vertical.json
  • Edit:   $EDITOR .graph-analytics/industry_vertical.json
  • Validate: python -m graph_analytics_ai.cli validate-vertical
  • Promote: python -m graph_analytics_ai.cli promote-vertical supply_chain

Continue with analysis? [Y/n]
```

### Phase 3: Pattern Detector Generation (Future Enhancement)

**Currently:** Generate pattern definitions (metadata)

**Future:** Generate actual Python pattern detector functions

```python
# Auto-generate this from pattern definitions
def detect_wcc_supply_chain_patterns(results, total_nodes):
    """Auto-generated pattern detector for supply chain WCC analysis."""
    patterns = []
    
    # Generated from pattern_definitions["wcc"][0]
    # Pattern: single_point_of_failure
    components = group_by_component(results)
    for comp_id, nodes in components.items():
        # Check for suppliers with no alternatives
        suppliers = [n for n in nodes if n.get("type") == "Supplier"]
        for supplier in suppliers:
            downstream = count_downstream_dependencies(supplier)
            if downstream > 10 and no_alternatives(supplier):
                patterns.append({
                    "type": "single_point_of_failure",
                    "supplier_id": supplier["id"],
                    "downstream_count": downstream,
                    "risk_level": "CRITICAL",
                    # ... rest of pattern
                })
    
    return patterns
```

---

## Example: Supply Chain Vertical Generation

### Input: business_requirements.md

```markdown
# Supply Chain Analytics Requirements

## 1. Domain Overview
**Industry:** Supply Chain & Logistics
**Primary Function:** Optimize supply chain resilience and detect bottlenecks
**Target Users:** Supply chain analysts, procurement managers

## 2. Domain Terminology
**Currency:** USD
**Units:** units, pallets, containers, days (lead time)
**Key Terms:**
- Lead Time: Days from order to delivery
- SKU: Stock Keeping Unit (product identifier)
- Single Point of Failure: Sole supplier for critical component

**Regulations:**
- Import/Export compliance
- Customs documentation

**Thresholds:**
- Critical inventory: < 7 days on hand
- High concentration risk: > 30% volume from single supplier

## 3. Graph Structure
**Nodes:**
- Supplier: Manufacturers and vendors (500-1000 nodes)
- Warehouse: Distribution centers (20-50 nodes)
- Product: SKUs (10,000+ nodes)

**Edges:**
- suppliesTo: Supplier → Warehouse relationships
- stores: Warehouse → Product inventory
- dependsOn: Product → Supplier dependencies

## 4. Key Metrics
- Lead time variance: Std dev of delivery times
- Inventory turnover: Sales / Average inventory
- Geographic concentration: % of suppliers in one region

## 5. Patterns to Detect
**Critical:**
- Single point of failure: One supplier for critical component
- Geographic concentration: >50% suppliers in one region

**Valuable:**
- Diversified supply: Multiple suppliers per component
- Regional distribution: Balanced geographic spread
```

### Output: .graph-analytics/industry_vertical.json

```json
{
  "metadata": {
    "name": "supply_chain",
    "display_name": "Supply Chain & Logistics",
    "generated_at": "2026-02-10T10:30:00Z"
  },
  "analysis_prompt": "You are analyzing a supply chain and logistics graph...\n\n## Domain Context\n\n**Nodes:**\n- Supplier: Manufacturers and vendors\n- Warehouse: Distribution centers and storage facilities\n- Product: SKUs and inventory items\n\n**Edges:**\n- suppliesTo: Supply relationships\n- stores: Inventory storage\n- dependsOn: Supply dependencies\n\n## Key Metrics\n\n1. **Supply Chain Resilience:**\n   - Single points of failure (suppliers with no backup)\n   - Geographic concentration (>30% in one region = high risk)\n   - Lead time variance (high variance = unreliable supply)\n\n2. **Inventory Optimization:**\n   - Critical inventory levels (< 7 days = CRITICAL)\n   - Turnover rates\n   - Storage efficiency\n\n...",
  "pattern_definitions": { /* ... */ }
}
```

---

## CLI Commands

### 1. Generate Vertical

```bash
# Auto-generate from business requirements
cd ~/code/my-supply-chain-project
python -m graph_analytics_ai.cli generate-vertical \
  --input docs/business_requirements.md \
  --graph-name supply_chain_graph \
  --output .graph-analytics/industry_vertical.json

# With validation
python -m graph_analytics_ai.cli generate-vertical \
  --input docs/business_requirements.md \
  --graph-name supply_chain_graph \
  --validate \
  --interactive  # Ask for user confirmation
```

### 2. Validate Vertical

```bash
# Check if vertical is valid
python -m graph_analytics_ai.cli validate-vertical \
  .graph-analytics/industry_vertical.json
```

### 3. Promote to Platform

```bash
# Promote custom vertical to platform registry (for sharing)
python -m graph_analytics_ai.cli promote-vertical \
  --source .graph-analytics/industry_vertical.json \
  --target supply_chain \
  --description "Supply chain and logistics analytics"
```

### 4. List Verticals

```bash
# List all available verticals
python -m graph_analytics_ai.cli list-verticals

# Output:
# Built-in Verticals:
#   - adtech (Ad-Tech / Identity Resolution)
#   - fintech (FinTech / Financial Services)
#   - fraud_intelligence (Fraud Intelligence - Indian Banking)
#   - social (Social Networks)
#   - generic (Generic Analysis)
#
# Platform Custom Verticals:
#   - supply_chain (Supply Chain & Logistics)
#   - healthcare (Healthcare Networks)
#
# Project Custom Vertical:
#   ✓ Found in .graph-analytics/industry_vertical.json
#   - supply_chain_retail (Supply Chain - Retail Focus)
```

---

## Implementation Phases

### Phase 1: MVP (Weeks 1-2)

**Goal:** Basic auto-generation from business requirements

**Deliverables:**
- [ ] IndustryVerticalAgent basic implementation
- [ ] JSON schema for custom verticals
- [ ] Load custom vertical from `.graph-analytics/`
- [ ] Generate basic prompt from business requirements
- [ ] Save to client project
- [ ] CLI: `generate-vertical`, `validate-vertical`

**Usage:**
```python
runner = AgenticWorkflowRunner(
    graph_name="my_graph",
    industry="auto"  # Triggers generation
)
```

### Phase 2: Enhanced Generation (Weeks 3-4)

**Goal:** Better prompt quality, pattern definitions

**Deliverables:**
- [ ] Extract domain terminology automatically
- [ ] Generate pattern definitions for WCC/PageRank
- [ ] Support multiple input documents
- [ ] Interactive refinement workflow
- [ ] Better validation

**Example output:**
- Richer prompts with specific metrics
- Pattern templates for common algorithms
- Risk classification framework

### Phase 3: Pattern Detector Generation (Weeks 5-6)

**Goal:** Generate actual Python pattern detector code

**Deliverables:**
- [ ] Code generation from pattern definitions
- [ ] Pattern detector templates
- [ ] Safe execution sandbox
- [ ] Testing framework for generated patterns

**Advanced usage:**
```python
# Generated pattern detectors are used automatically
runner = AgenticWorkflowRunner(
    graph_name="my_graph",
    industry="supply_chain",  # Uses generated patterns
    use_generated_patterns=True  # NEW flag
)
```

### Phase 4: Sharing & Registry (Weeks 7-8)

**Goal:** Share custom verticals across projects

**Deliverables:**
- [ ] Platform custom vertical registry
- [ ] `promote-vertical` command
- [ ] Vertical marketplace/catalog
- [ ] Version management
- [ ] Community contributions

---

## Migration Path

### For Existing Built-in Verticals

**Option 1:** Keep as built-in (no changes)

**Option 2:** Convert to JSON format for consistency

```python
# Export existing verticals to JSON
python -m graph_analytics_ai.cli export-builtin-verticals \
  --output graph_analytics_ai/ai/reporting/verticals/

# Creates:
#   verticals/adtech.json
#   verticals/fintech.json
#   verticals/fraud_intelligence.json
#   verticals/social.json
```

### For Existing Projects

**fraud-intelligence project:**

```bash
cd ~/code/fraud-intelligence

# Option 1: Use existing fraud_intelligence built-in
python run_fraud_analysis.py  # Works as before

# Option 2: Generate custom refined vertical
python -m graph_analytics_ai.cli generate-vertical \
  --input docs/business_requirements.md \
  --base-vertical fraud_intelligence \
  --refine  # Builds on existing, adds custom patterns
```

---

## Security & Validation

### Validation Rules

1. **Schema Validation:**
   - Required fields present
   - Valid JSON structure
   - Reasonable prompt length (< 10K tokens)

2. **Content Validation:**
   - No code injection in prompts
   - No malicious patterns
   - Reasonable pattern counts

3. **User Validation:**
   - Review flag: `user_validated: false` initially
   - User must explicitly approve
   - Can add notes/refinements

### Safety

```python
class VerticalValidator:
    """Validate generated verticals for safety and quality."""
    
    def validate_schema(self, vertical: Dict) -> List[str]:
        """Check required fields and structure."""
        
    def validate_content(self, vertical: Dict) -> List[str]:
        """Check for malicious content."""
        
    def validate_quality(self, vertical: Dict) -> List[str]:
        """Check prompt quality and completeness."""
```

---

## User Experience

### First Run (Auto-generate)

```bash
$ python run_fraud_analysis.py

Initializing workflow runner...
Industry: 'fraud_intelligence' found in built-in verticals.
✓ Using built-in fraud_intelligence vertical
...
```

### First Run (Unknown Industry)

```bash
$ python run_supply_chain_analysis.py

Initializing workflow runner...
Industry: 'supply_chain' not found in built-in verticals.
Checking for custom vertical in project...
No custom vertical found at .graph-analytics/industry_vertical.json

Would you like to generate a custom vertical from your business requirements? [Y/n]: y

Generating custom vertical...
  ✓ Analyzing business requirements (docs/business_requirements.md)
  ✓ Extracting graph schema from supply_chain_graph
  ✓ Identifying domain entities (5 node types, 4 edge types)
  ✓ Generating industry-specific prompt (2,847 tokens)
  ✓ Defining pattern templates (6 patterns for WCC/PageRank)
  ✓ Saving to .graph-analytics/industry_vertical.json

Custom vertical generated: Supply Chain & Logistics

Please review the generated vertical:
  File: .graph-analytics/industry_vertical.json
  
You can:
  • Edit the file to refine prompts and patterns
  • Add custom terminology in the terminology section
  • Adjust risk thresholds
  
Proceed with analysis using generated vertical? [Y/n]: y

✓ Registered custom vertical: supply_chain
Running workflow...
...
```

### Second Run (Use Existing)

```bash
$ python run_supply_chain_analysis.py

Initializing workflow runner...
Industry: 'supply_chain' not found in built-in verticals.
✓ Found custom vertical: Supply Chain & Logistics
  Generated: 2026-02-10
  User validated: Yes
✓ Using custom vertical

Running workflow...
...
```

---

## Testing Strategy

### Unit Tests

```python
# test_industry_vertical_agent.py

async def test_generate_vertical_from_requirements():
    """Test generating vertical from business requirements."""
    agent = IndustryVerticalAgent()
    
    business_reqs = """
    # Supply Chain Requirements
    Industry: Supply Chain
    Key entities: Supplier, Warehouse, Product
    Key patterns: Single point of failure, Geographic concentration
    """
    
    vertical = await agent.generate_vertical(
        business_requirements=business_reqs,
        graph_name="test_graph"
    )
    
    assert vertical["metadata"]["name"] == "supply_chain"
    assert "Supplier" in vertical["analysis_prompt"]
    assert len(vertical["pattern_definitions"]["wcc"]) > 0

async def test_load_custom_vertical():
    """Test loading custom vertical from file."""
    vertical = load_custom_vertical(Path("/test/project"))
    assert vertical is not None
    assert vertical["metadata"]["name"] == "supply_chain"
```

### Integration Tests

```python
async def test_workflow_with_auto_generated_vertical():
    """Test full workflow with auto-generated vertical."""
    # Create test project structure
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create business requirements
    (project_dir / "docs").mkdir()
    (project_dir / "docs" / "business_requirements.md").write_text("""
    # Supply Chain Requirements
    ...
    """)
    
    # Run workflow with auto-generation
    os.chdir(project_dir)
    runner = AgenticWorkflowRunner(
        graph_name="test_supply_chain",
        industry="auto"
    )
    
    state = await runner.run_workflow_async(
        input_documents=["docs/business_requirements.md"]
    )
    
    # Check vertical was generated
    vertical_path = project_dir / ".graph-analytics" / "industry_vertical.json"
    assert vertical_path.exists()
    
    # Check reports use custom vertical
    assert "supply chain" in state.reports[0].title.lower()
```

---

## Documentation Updates

### User Guides

1. **NEW: "Creating Custom Industry Verticals"**
   - How to structure business requirements
   - What information is needed
   - How to refine generated verticals
   - Best practices

2. **UPDATE: "Getting Started"**
   - Add section on `industry="auto"`
   - Explain custom vertical workflow

3. **NEW: "Custom Vertical Reference"**
   - JSON schema documentation
   - Field descriptions
   - Examples

### API Documentation

```python
class AgenticWorkflowRunner:
    """
    Run agentic workflow with optional auto-generated custom verticals.
    
    Args:
        graph_name: Name of the graph to analyze
        industry: Industry vertical to use. Options:
            - Built-in: "adtech", "fintech", "fraud_intelligence", "social", "generic"
            - Custom: Any name (will look for .graph-analytics/industry_vertical.json)
            - Auto-generate: "auto" (generates from business requirements)
        auto_generate_vertical: If True, automatically generate custom vertical
            when industry is not found (default: True)
    
    Examples:
        # Use built-in vertical
        runner = AgenticWorkflowRunner(graph_name="my_graph", industry="fintech")
        
        # Auto-generate custom vertical
        runner = AgenticWorkflowRunner(graph_name="my_graph", industry="auto")
        
        # Use specific custom vertical
        runner = AgenticWorkflowRunner(graph_name="my_graph", industry="supply_chain")
    """
```

---

## File Structure

### agentic-graph-analytics

```
graph_analytics_ai/
  ai/
    agents/
      industry_vertical.py          ← NEW: IndustryVerticalAgent
    reporting/
      custom_prompts.py             ← NEW: Custom vertical loading
      verticals/                    ← NEW: Platform custom verticals
        supply_chain.json
        healthcare.json
      prompts.py                    ← UPDATE: Add custom loading
      algorithm_insights.py         ← UPDATE: Support custom patterns
  cli/
    generate_vertical.py            ← NEW: CLI for vertical generation
    validate_vertical.py            ← NEW: CLI for validation
    promote_vertical.py             ← NEW: CLI to promote to platform
    list_verticals.py               ← NEW: CLI to list all verticals

templates/
  business_requirements_template.md  ← NEW: Enhanced template
  industry_vertical_schema.json      ← NEW: JSON schema

docs/
  guides/
    creating_custom_verticals.md     ← NEW: User guide
    custom_vertical_reference.md     ← NEW: API reference
```

### Client Project (e.g., fraud-intelligence)

```
fraud-intelligence/
  .graph-analytics/                  ← NEW: Hidden config directory
    industry_vertical.json           ← Generated custom vertical
    vertical_generation.log          ← Generation log
    user_notes.md                    ← User refinements
  docs/
    business_requirements.md         ← Enhanced with new sections
    domain_description.md
  ...
```

---

## Comparison: Current vs. With Auto-Generation

### Current State

```python
# Only works with built-in verticals
runner = AgenticWorkflowRunner(
    graph_name="supply_chain",
    industry="generic"  # Suboptimal - no domain knowledge
)

# To add supply chain vertical:
# 1. Edit prompts.py (add SUPPLY_CHAIN_PROMPT)
# 2. Edit algorithm_insights.py (add pattern detectors)
# 3. Commit to platform repo
# 4. Reinstall platform
```

### With Auto-Generation

```python
# First run - auto-generates
runner = AgenticWorkflowRunner(
    graph_name="supply_chain",
    industry="auto"  # Generates custom vertical from business reqs
)
# → Creates .graph-analytics/industry_vertical.json

# Second run - uses existing
runner = AgenticWorkflowRunner(
    graph_name="supply_chain",
    industry="supply_chain"  # Uses custom vertical
)

# To share across projects:
# python -m graph_analytics_ai.cli promote-vertical supply_chain
```

---

## Benefits

### For Users

1. **No Code Required:** Generate custom verticals from requirements docs
2. **Instant Customization:** Domain-specific analysis without platform changes
3. **Project Isolation:** Each project has its own custom vertical
4. **Easy Refinement:** Edit JSON file to improve prompts
5. **Shareable:** Promote good verticals to platform registry

### For Platform

1. **Extensibility:** Unlimited industry support without code changes
2. **Community:** Users contribute custom verticals
3. **Validation:** Real-world usage improves vertical quality
4. **Reduced Maintenance:** Less code in platform repo

### For Business

1. **Faster Time to Value:** Don't wait for platform updates
2. **Better Insights:** Domain-specific analysis from day one
3. **Adaptability:** Verticals evolve with business needs
4. **Cost Effective:** No custom development required

---

## Risks & Mitigation

### Risk 1: Generated Prompts Are Low Quality

**Mitigation:**
- User review and validation required
- Provide examples in business requirements
- Iterative refinement workflow
- Option to base on existing vertical

### Risk 2: Security Concerns (Malicious Prompts)

**Mitigation:**
- Content validation before use
- Sandboxed execution for generated patterns
- User approval required
- Audit log of generations

### Risk 3: Inconsistent Quality Across Custom Verticals

**Mitigation:**
- Enhanced business requirements template
- Quality scoring for generated verticals
- Best practice examples
- Community review for promoted verticals

### Risk 4: Storage/Version Conflicts

**Mitigation:**
- Clear storage hierarchy (client > platform > built-in)
- Version tracking in metadata
- Upgrade warnings for old verticals
- Export/import utilities

---

## Success Metrics

### Short-term (MVP)

- [ ] Generate valid custom vertical from business requirements (100% success rate)
- [ ] User can run workflow with auto-generated vertical
- [ ] Generated prompts include domain terminology
- [ ] Storage in client project works

### Medium-term (6 months)

- [ ] 10+ custom verticals created by users
- [ ] 3+ custom verticals promoted to platform
- [ ] 80%+ user satisfaction with generated prompts
- [ ] Reduce platform code changes for new industries by 90%

### Long-term (1 year)

- [ ] 50+ custom verticals in community registry
- [ ] Generated pattern detectors work reliably
- [ ] Custom verticals as accurate as built-in
- [ ] Zero platform code needed for new industries

---

## Next Steps

### Immediate (This Week)

1. **Review this plan** - Get feedback, refine approach
2. **Prototype IndustryVerticalAgent** - Basic prompt generation
3. **Update business requirements template** - Add new required sections
4. **Test with fraud-intelligence** - Generate custom vertical from existing docs

### Phase 1 MVP (Next 2 Weeks)

1. Implement IndustryVerticalAgent (basic)
2. Create JSON schema for custom verticals
3. Implement custom vertical loading
4. Create CLI commands
5. Test end-to-end with sample project

### Phase 2 Enhancement (Weeks 3-4)

1. Improve prompt generation quality
2. Add pattern definition generation
3. Interactive refinement workflow
4. Better validation

---

## Questions for Discussion

1. **Business Requirements:** Are current docs sufficient or need more structure?
2. **Storage:** Client project only, or support platform registry from start?
3. **Validation:** How much user review before using generated vertical?
4. **Pattern Detectors:** Generate code (advanced) or just metadata (MVP)?
5. **Sharing:** Build community registry/marketplace?
6. **Pricing:** Free feature or premium/enterprise?

---

**Document Version:** 1.0  
**Date:** February 10, 2026  
**Author:** Graph Analytics AI Platform Team  
**Status:** PROPOSAL - Pending Review
