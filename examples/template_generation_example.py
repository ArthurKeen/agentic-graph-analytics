"""
Example: GAE Template Generation

Demonstrates how to generate GAE analysis templates from use cases.
Shows the complete flow from requirements → use cases → templates.
"""

from graph_analytics_ai.db_connection import get_db_connection
from graph_analytics_ai.ai.schema.extractor import create_extractor
from graph_analytics_ai.ai.schema.analyzer import SchemaAnalyzer
from graph_analytics_ai.ai.llm import create_llm_provider
from graph_analytics_ai.ai.generation.use_cases import UseCaseGenerator
from graph_analytics_ai.ai.templates import TemplateGenerator
from graph_analytics_ai.ai.documents.models import (
    ExtractedRequirements,
    Requirement,
    Objective,
    Priority,
    RequirementType
)
import os


def example_template_generation():
    """Generate GAE templates from use cases."""
    
    print("=" * 70)
    print("Example: GAE Template Generation")
    print("=" * 70)
    print()
    
    # ========================================================================
    # 1. Extract Schema from Real Cluster
    # ========================================================================
    print("1️⃣  Extracting schema from cluster...")
    
    get_db_connection()
    extractor = create_extractor(
        endpoint=os.getenv('ARANGO_ENDPOINT'),
        database=os.getenv('ARANGO_DATABASE'),
        username='root',
        password=os.getenv('ARANGO_PASSWORD')
    )
    schema = extractor.extract()
    
    print(f"   ✓ Extracted {len(schema.vertex_collections)} vertex collections")
    print(f"   ✓ Extracted {len(schema.edge_collections)} edge collections")
    print(f"   ✓ Total: {schema.total_documents} documents, {schema.total_edges} edges")
    print()
    
    # ========================================================================
    # 2. Analyze Schema
    # ========================================================================
    print("2️⃣  Analyzing schema...")
    
    provider = create_llm_provider()
    analyzer = SchemaAnalyzer(provider)
    
    try:
        analysis = analyzer.analyze(schema)
        print(f"   ✓ Domain: {analysis.domain}")
        print(f"   ✓ Complexity: {analysis.complexity_score:.1f}/10")
        print(f"   ✓ Key entities: {', '.join(analysis.key_entities[:3])}")
    except Exception as e:
        print(f"   ⚠️  LLM analysis failed (using fallback): {e}")
        analysis = analyzer._create_fallback_analysis(schema)
    
    print()
    
    # ========================================================================
    # 3. Create Mock Requirements
    # ========================================================================
    print("3️⃣  Creating sample requirements...")
    
    # Create mock extracted requirements for demo
    requirements = ExtractedRequirements(
        domain="E-commerce Analytics",
        summary="Analyze customer behavior and product performance",
        documents=[],
        objectives=[
            Objective(
                id="OBJ-001",
                title="Identify Influential Customers",
                description="Find customers with high influence on purchase decisions",
                priority=Priority.CRITICAL,
                success_criteria=["Identify top 10% influencers", "Track influence metrics"]
            ),
            Objective(
                id="OBJ-002",
                title="Discover Customer Segments",
                description="Group customers into segments based on behavior",
                priority=Priority.HIGH,
                success_criteria=["Clear segment boundaries", "Actionable insights per segment"]
            ),
            Objective(
                id="OBJ-003",
                title="Product Recommendation Paths",
                description="Find shortest paths for product recommendations",
                priority=Priority.HIGH,
                success_criteria=["Identify common paths", "Reduce recommendation latency"]
            )
        ],
        requirements=[
            Requirement(
                id="REQ-001",
                text="System shall identify influential users using graph analytics",
                requirement_type=RequirementType.FUNCTIONAL,
                priority=Priority.CRITICAL
            ),
            Requirement(
                id="REQ-002",
                text="System shall detect customer communities and segments",
                requirement_type=RequirementType.FUNCTIONAL,
                priority=Priority.HIGH
            )
        ],
        stakeholders=[],
        constraints=[],
        risks=[]
    )
    
    print(f"   ✓ Created {len(requirements.objectives)} objectives")
    print(f"   ✓ Created {len(requirements.requirements)} requirements")
    print()
    
    # ========================================================================
    # 4. Generate Use Cases
    # ========================================================================
    print("4️⃣  Generating use cases...")
    
    use_case_generator = UseCaseGenerator()
    use_cases = use_case_generator.generate(
        extracted=requirements,
        schema_analysis=analysis
    )
    
    print(f"   ✓ Generated {len(use_cases)} use cases:")
    for uc in use_cases[:5]:  # Show first 5
        print(f"      • {uc.id}: {uc.title} [{uc.use_case_type.value}]")
    if len(use_cases) > 5:
        print(f"      ... and {len(use_cases) - 5} more")
    print()
    
    # ========================================================================
    # 5. Generate Templates
    # ========================================================================
    print("5️⃣  Generating GAE templates...")
    
    template_generator = TemplateGenerator(
        graph_name="ecommerce_graph",
        auto_optimize=True
    )
    
    templates = template_generator.generate_templates(
        use_cases=use_cases,
        schema=schema,
        schema_analysis=analysis
    )
    
    print(f"   ✓ Generated {len(templates)} GAE analysis templates")
    print()
    
    # ========================================================================
    # 6. Display Template Details
    # ========================================================================
    print("6️⃣  Template Details:")
    print()
    
    for i, template in enumerate(templates[:3], 1):  # Show first 3 in detail
        print(f"   Template {i}: {template.name}")
        print(f"   {'─' * 66}")
        print(f"   Algorithm: {template.algorithm.algorithm.value}")
        print(f"   Engine Size: {template.config.engine_size.value}")
        print(f"   Estimated Runtime: {template.estimated_runtime_seconds:.1f}s")
        print()
        
        print("   Parameters:")
        for key, value in template.algorithm.parameters.items():
            print(f"      • {key}: {value}")
        print()
        
        if template.config.vertex_collections:
            print(f"   Vertex Collections: {', '.join(template.config.vertex_collections)}")
        if template.config.edge_collections:
            print(f"   Edge Collections: {', '.join(template.config.edge_collections)}")
        
        print(f"   Result Collection: {template.config.result_collection}")
        print()
    
    if len(templates) > 3:
        print(f"   ... and {len(templates) - 3} more templates")
        print()
    
    # ========================================================================
    # 7. Show AnalysisConfig Format
    # ========================================================================
    print("7️⃣  Example AnalysisConfig (for GAE Orchestrator):")
    print()
    
    if templates:
        template = templates[0]
        config = template.to_analysis_config()
        
        print("   ```python")
        print("   analysis_config = {")
        for key, value in config.items():
            if isinstance(value, str):
                print(f"       '{key}': '{value}',")
            elif isinstance(value, list):
                if value:
                    print(f"       '{key}': {value},")
                else:
                    print(f"       '{key}': [],")
            else:
                print(f"       '{key}': {value},")
        print("   }")
        print("   ```")
        print()
    
    # ========================================================================
    # 8. Summary
    # ========================================================================
    print("=" * 70)
    print("✅ Template Generation Complete!")
    print("=" * 70)
    print()
    
    print("📊 Summary:")
    print(f"   • Schema: {schema.total_documents} documents, {schema.total_edges} edges")
    print(f"   • Objectives: {len(requirements.objectives)}")
    print(f"   • Use Cases: {len(use_cases)}")
    print(f"   • Templates: {len(templates)}")
    print()
    
    print("🎯 Templates Ready For:")
    print("   • GAE execution on AMP cluster")
    print("   • Parameter optimization")
    print("   • Batch analysis runs")
    print("   • Workflow automation")
    print()
    
    print("🚀 Next Steps:")
    print("   • Validate templates")
    print("   • Execute on GAE cluster")
    print("   • Analyze results")
    print("   • Generate reports")
    print()
    
    return templates


if __name__ == '__main__':
    templates = example_template_generation()

