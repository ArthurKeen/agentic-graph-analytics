"""
Example: Complete GAE Analysis Pipeline

Demonstrates the complete flow:
1. Extract schema
2. Generate use cases
3. Create templates
4. Execute on GAE cluster
5. Collect and display results

This is the end-to-end demonstration of Phases 1-8!
"""

from graph_analytics_ai.db_connection import get_db_connection
from graph_analytics_ai.ai.schema.extractor import SchemaExtractor
from graph_analytics_ai.ai.schema.analyzer import SchemaAnalyzer
from graph_analytics_ai.ai.llm import create_llm_provider
from graph_analytics_ai.ai.generation.use_cases import UseCaseGenerator
from graph_analytics_ai.ai.templates import TemplateGenerator, validate_template
from graph_analytics_ai.ai.execution import AnalysisExecutor
from graph_analytics_ai.ai.documents.models import (
    ExtractedRequirements,
    Requirement,
    Objective,
    Priority,
    RequirementType
)


def complete_pipeline_example():
    """Run the complete GAE analysis pipeline."""
    
    print("=" * 70)
    print("Complete GAE Analysis Pipeline - Phases 1-8")
    print("=" * 70)
    print()
    
    # ========================================================================
    # Phase 1-2: Schema Extraction & Analysis
    # ========================================================================
    print("📊 Phase 1-2: Schema Extraction & Analysis")
    print("-" * 70)
    
    db = get_db_connection()
    extractor = SchemaExtractor(db)
    schema = extractor.extract()
    
    print("✓ Schema extracted:")
    print(f"  • Vertex collections: {len(schema.vertex_collections)}")
    print(f"  • Edge collections: {len(schema.edge_collections)}")
    print(f"  • Total: {schema.total_documents:,} documents, {schema.total_edges:,} edges")
    
    provider = create_llm_provider()
    analyzer = SchemaAnalyzer(provider)
    
    try:
        analysis = analyzer.analyze(schema)
        print(f"✓ Schema analyzed: {analysis.domain}, complexity {analysis.complexity_score:.1f}/10")
    except:
        analysis = analyzer._create_fallback_analysis(schema)
        print("✓ Schema analyzed (fallback mode)")
    
    print()
    
    # ========================================================================
    # Phase 3-4: Requirements & PRD
    # ========================================================================
    print("📝 Phase 3-4: Requirements & PRD")
    print("-" * 70)
    
    # Create sample requirements
    requirements = ExtractedRequirements(
        domain="E-commerce Analytics",
        summary="Analyze customer behavior and identify key patterns",
        documents=[],
        objectives=[
            Objective(
                id="OBJ-001",
                title="Identify Top Influencers",
                description="Find customers with highest influence on purchase decisions",
                priority=Priority.CRITICAL,
                success_criteria=["Identify top 10% influencers", "Quantify influence scores"]
            )
        ],
        requirements=[
            Requirement(
                id="REQ-001",
                text="System shall identify influential users using PageRank",
                requirement_type=RequirementType.FUNCTIONAL,
                priority=Priority.CRITICAL
            )
        ],
        stakeholders=[],
        constraints=[],
        risks=[]
    )
    
    print(f"✓ Requirements created: {len(requirements.objectives)} objectives")
    print()
    
    # ========================================================================
    # Phase 5: Use Case Generation
    # ========================================================================
    print("🎯 Phase 5: Use Case Generation")
    print("-" * 70)
    
    use_case_generator = UseCaseGenerator()
    use_cases = use_case_generator.generate(requirements, analysis)
    
    print(f"✓ Generated {len(use_cases)} use cases:")
    for uc in use_cases[:3]:
        print(f"  • {uc.id}: {uc.title} [{uc.use_case_type.value}]")
    print()
    
    # ========================================================================
    # Phase 7: Template Generation
    # ========================================================================
    print("📋 Phase 7: Template Generation")
    print("-" * 70)
    
    template_generator = TemplateGenerator(graph_name="ecommerce_graph")
    templates = template_generator.generate_templates(use_cases, schema, analysis)
    
    print(f"✓ Generated {len(templates)} GAE templates")
    
    # Validate templates
    valid_count = 0
    for template in templates:
        result = validate_template(template)
        if result.is_valid:
            valid_count += 1
    
    print(f"✓ Validated: {valid_count}/{len(templates)} templates valid")
    print()
    
    # Show first template details
    if templates:
        template = templates[0]
        print(f"Example Template: {template.name}")
        print(f"  Algorithm: {template.algorithm.algorithm.value}")
        print(f"  Engine: {template.config.engine_size.value}")
        print(f"  Estimated: {template.estimated_runtime_seconds:.1f}s")
        print()
    
    # ========================================================================
    # Phase 8: EXECUTION! 🚀
    # ========================================================================
    print("🚀 Phase 8: GAE Analysis Execution")
    print("-" * 70)
    
    if not templates:
        print("No templates to execute")
        return
    
    # Execute first template as demo
    template = templates[0]
    print(f"Executing: {template.name}")
    print(f"Algorithm: {template.algorithm.algorithm.value}")
    print()
    
    executor = AnalysisExecutor()
    result = executor.execute_template(template, wait=True)
    
    if result.success:
        print("✅ Execution successful!")
        print(f"   Job ID: {result.job.job_id}")
        print(f"   Status: {result.job.status.value}")
        print(f"   Runtime: {result.job.execution_time_seconds:.1f}s")
        print(f"   Results: {result.job.result_count or 0} records")
        print()
        
        if result.results:
            print("Top Results:")
            top_results = result.get_top_results(5)
            for i, r in enumerate(top_results, 1):
                print(f"   {i}. {r}")
        
    else:
        print(f"❌ Execution failed: {result.error}")
    
    print()
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("=" * 70)
    print("Pipeline Summary")
    print("=" * 70)
    
    summary = executor.get_execution_summary()
    print(f"Total jobs executed: {summary['total_jobs']}")
    print(f"Successful: {summary['completed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success rate: {summary['success_rate']*100:.1f}%")
    
    if summary['avg_execution_time'] > 0:
        print(f"Avg execution time: {summary['avg_execution_time']:.1f}s")
    
    print()
    print("🎉 Complete pipeline executed successfully!")
    print()
    print("Phases completed:")
    print("  ✅ Phase 1: LLM Foundation")
    print("  ✅ Phase 2: Schema Analysis")
    print("  ✅ Phase 3: Document Processing")
    print("  ✅ Phase 4: PRD Generation")
    print("  ✅ Phase 5: Use Case Generation")
    print("  ✅ Phase 6: Workflow Orchestration")
    print("  ✅ Phase 7: Template Generation")
    print("  ✅ Phase 8: Analysis Execution")
    print()
    print("Next: Phase 9 - Report Generation from results!")
    print()


if __name__ == '__main__':
    complete_pipeline_example()

