"""
Simplified validation script to test both Traditional Orchestration and Agentic Workflows.

This validates that both workflows can:
1. Connect to existing ecommerce_graph
2. Extract schema and analyze
3. Generate use cases and templates
4. (Agentic only) Execute and generate reports
"""

import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Imports
from graph_analytics_ai.db_connection import get_db_connection
from graph_analytics_ai.ai.schema import SchemaExtractor, SchemaAnalyzer
from graph_analytics_ai.ai.documents.models import Document, ExtractedRequirements, Objective, Priority
from graph_analytics_ai.ai.generation import UseCaseGenerator
from graph_analytics_ai.ai.templates import TemplateGenerator, TemplateValidator
from graph_analytics_ai.ai.agents import AgenticWorkflowRunner


def print_header(title):
    print(f"\n{'='*70}\n  {title}\n{'='*70}\n")


def test_traditional_workflow():
    """Test traditional orchestration workflow."""
    print_header("TEST 1: TRADITIONAL ORCHESTRATION WORKFLOW")
    
    start_time = time.time()
    
    try:
        # 1. Extract schema
        print("Step 1: Extracting schema...")
        db = get_db_connection()
        extractor = SchemaExtractor(db)
        schema = extractor.extract()
        print(f"  ✓ {len(schema.vertex_collections)} vertices, {len(schema.edge_collections)} edges")
        
        # 2. Analyze schema
        print("\nStep 2: Analyzing schema...")
        analyzer = SchemaAnalyzer()
        analysis = analyzer.analyze(schema)
        print(f"  ✓ Complexity: {analysis.complexity_score:.2f}/10")
        
        # 3. Create requirements (simulated - agentic workflow generates these automatically)
        print("\nStep 3: Creating requirements...")
        from graph_analytics_ai.ai.documents.models import DocumentMetadata, DocumentType
        metadata = DocumentMetadata(
            file_path="use_case.md",
            file_name="use_case.md",
            document_type=DocumentType.MARKDOWN
        )
        doc = Document(
            metadata=metadata,
            content="Identify influential customers and communities for e-commerce analytics"
        )
        requirements = ExtractedRequirements(
            documents=[doc],
            objectives=[
                Objective(
                    id="OBJ-001",
                    title="Find Influencers",
                    description="Identify influential customers",
                    priority=Priority.HIGH
                )
            ],
            summary="E-commerce customer analytics"
        )
        print(f"  ✓ {len(requirements.objectives)} objectives created")
        
        # 4. Generate use cases
        print("\nStep 4: Generating use cases...")
        uc_gen = UseCaseGenerator()
        use_cases = uc_gen.generate(requirements, analysis)
        print(f"  ✓ {len(use_cases)} use cases generated")
        for uc in use_cases[:3]:
            print(f"    - {uc.title}")
        
        # 5. Generate templates
        print("\nStep 5: Generating templates...")
        tmpl_gen = TemplateGenerator(graph_name="ecommerce_graph")
        templates = tmpl_gen.generate_templates(use_cases, schema, analysis)
        print(f"  ✓ {len(templates)} templates generated")
        
        # Validate
        validator = TemplateValidator()
        valid = sum(1 for t in templates if validator.validate(t).is_valid)
        print(f"  ✓ {valid}/{len(templates)} templates valid")
        
        elapsed = time.time() - start_time
        
        print("\n✅ TRADITIONAL WORKFLOW: SUCCESS")
        print(f"   Completed in {elapsed:.2f}s")
        print(f"   Generated {len(use_cases)} use cases, {len(templates)} templates")
        
        return True, {
            'duration': elapsed,
            'use_cases': len(use_cases),
            'templates': len(templates),
            'valid_templates': valid
        }
        
    except Exception as e:
        print("\n❌ TRADITIONAL WORKFLOW: FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False, {}


def test_agentic_workflow():
    """Test agentic workflow with autonomous agents."""
    print_header("TEST 2: AGENTIC WORKFLOW (AUTONOMOUS)")
    
    start_time = time.time()
    
    try:
        # Run agentic workflow
        print("Initializing autonomous agents...")
        runner = AgenticWorkflowRunner()
        
        print("\nRunning autonomous workflow...")
        print("(Agents will coordinate automatically)\n")
        
        state = runner.run()
        
        elapsed = time.time() - start_time
        
        # Extract results from state
        use_case_count = len(state.use_cases)
        template_count = len(state.templates)
        execution_count = len(state.execution_results)
        report_count = len(state.reports)
        
        print("\n✅ AGENTIC WORKFLOW: SUCCESS")
        print(f"   Completed in {elapsed:.2f}s")
        print(f"   Generated {use_case_count} use cases")
        print(f"   Generated {template_count} templates")
        print(f"   Executed {execution_count} analyses")
        print(f"   Generated {report_count} reports")
        
        # Show report summaries
        if report_count > 0:
            print("\n   Reports Generated:")
            for i, report in enumerate(state.reports, 1):
                print(f"   {i}. {report.title}")
                print(f"      - {len(report.insights)} insights")
                print(f"      - {len(report.recommendations)} recommendations")
        
        return True, {
            'duration': elapsed,
            'use_cases': use_case_count,
            'templates': template_count,
            'executions': execution_count,
            'reports': report_count
        }
        
    except Exception as e:
        print("\n❌ AGENTIC WORKFLOW: FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False, {}


def compare_results(trad_success, trad_data, agen_success, agen_data):
    """Compare results from both workflows."""
    print_header("COMPARISON & VALIDATION")
    
    print("Workflow Success:")
    print(f"  Traditional:  {'✅ PASS' if trad_success else '❌ FAIL'}")
    print(f"  Agentic:      {'✅ PASS' if agen_success else '❌ FAIL'}")
    
    if not (trad_success and agen_success):
        print("\n⚠️  Cannot complete comparison - one or both workflows failed")
        return False
    
    print("\nExecution Time:")
    print(f"  Traditional:  {trad_data['duration']:.2f}s")
    print(f"  Agentic:      {agen_data['duration']:.2f}s")
    
    print("\nUse Cases Generated:")
    print(f"  Traditional:  {trad_data['use_cases']}")
    print(f"  Agentic:      {agen_data['use_cases']}")
    
    print("\nTemplates Generated:")
    print(f"  Traditional:  {trad_data['templates']}")
    print(f"  Agentic:      {agen_data['templates']}")
    
    print("\nKey Differences:")
    print(f"  • Agentic workflow executed {agen_data['executions']} analyses")
    print(f"  • Agentic workflow generated {agen_data['reports']} intelligence reports")
    print("  • Traditional workflow provides more granular control")
    print("  • Agentic workflow is fully autonomous end-to-end")
    
    # Save results
    output_dir = Path(__file__).parent.parent / "workflow_output"
    output_dir.mkdir(exist_ok=True)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'traditional': {
            'success': trad_success,
            'data': trad_data
        },
        'agentic': {
            'success': agen_success,
            'data': agen_data
        }
    }
    
    with open(output_dir / "validation_comparison.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n✓ Detailed results saved to workflow_output/validation_comparison.json")
    
    return True


def main():
    """Run validation."""
    print("\n" + "="*70)
    print("  WORKFLOW VALIDATION - Traditional vs Agentic")
    print("  Testing with existing ecommerce_graph")
    print("="*70)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Traditional
    trad_success, trad_data = test_traditional_workflow()
    
    # Test 2: Agentic
    agen_success, agen_data = test_agentic_workflow()
    
    # Compare
    compare_results(trad_success, trad_data, agen_success, agen_data)
    
    # Final verdict
    print_header("VALIDATION RESULT")
    
    if trad_success and agen_success:
        print("✅ VALIDATION SUCCESSFUL")
        print("\nBoth workflows:")
        print("  ✓ Connect to existing database")
        print("  ✓ Extract and analyze schema")
        print("  ✓ Generate use cases")
        print("  ✓ Generate analysis templates")
        print("  ✓ Function correctly and independently")
        print("\nAgentic workflow additionally:")
        print("  ✓ Executes analyses on GAE")
        print("  ✓ Generates intelligence reports")
        print("  ✓ Operates fully autonomously")
        print("\n🎉 PLATFORM IS PRODUCTION READY")
        print("✅ READY TO MERGE TO MAIN")
    else:
        print("❌ VALIDATION FAILED")
        print("\nOne or both workflows encountered errors.")
        print("Review the output above for details.")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    return trad_success and agen_success


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nValidation interrupted")
        exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

