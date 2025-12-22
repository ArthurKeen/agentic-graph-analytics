"""
GAE Analysis Executor.

Executes GAE analysis templates using the existing GAEOrchestrator.
Provides high-level interface with monitoring and result collection.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from ...gae_orchestrator import GAEOrchestrator, AnalysisConfig
from ..templates.models import AnalysisTemplate
from .models import AnalysisJob, ExecutionResult, ExecutionStatus, ExecutionConfig


class AnalysisExecutor:
    """
    Executes GAE analysis templates on ArangoDB clusters.

    Provides high-level interface for:
    - Template execution
    - Job monitoring
    - Result collection
    - Batch execution
    - Error handling

    Example:
        >>> from graph_analytics_ai.ai.execution import AnalysisExecutor
        >>> from graph_analytics_ai.ai.templates import TemplateGenerator
        >>>
        >>> # Generate templates
        >>> generator = TemplateGenerator()
        >>> templates = generator.generate_templates(use_cases, schema)
        >>>
        >>> # Execute on cluster
        >>> executor = AnalysisExecutor()
        >>> result = executor.execute_template(templates[0])
        >>>
        >>> if result.success:
        ...     print(f"Analysis complete! {len(result.results)} results")
        ...     top_results = result.get_top_results(10)
    """

    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        orchestrator: Optional[GAEOrchestrator] = None,
    ):
        """
        Initialize analysis executor.

        Args:
            config: Execution configuration (uses defaults if None)
            orchestrator: Existing orchestrator (creates new if None)
        """
        self.config = config or ExecutionConfig()
        self.orchestrator = orchestrator or GAEOrchestrator()
        self.job_history: List[AnalysisJob] = []

    def execute_template(
        self, template: AnalysisTemplate, wait: bool = True
    ) -> ExecutionResult:
        """
        Execute a single analysis template.

        Args:
            template: Template to execute
            wait: Whether to wait for completion

        Returns:
            ExecutionResult with job info and results
        """
        # Convert template to AnalysisConfig
        analysis_config = self._template_to_config(template)

        # Create job record
        job = AnalysisJob(
            job_id="",  # Will be set after submission
            template_name=template.name,
            algorithm=template.algorithm.algorithm.value,
            status=ExecutionStatus.PENDING,
            submitted_at=datetime.now(),
            result_collection=template.config.result_collection,
            metadata={
                "use_case_id": template.use_case_id,
                "engine_size": template.config.engine_size.value,
                "estimated_runtime": template.estimated_runtime_seconds,
            },
        )

        try:
            # Submit job
            job.status = ExecutionStatus.SUBMITTED
            job_id = self._submit_job(analysis_config)
            job.job_id = job_id

            if self.config.store_job_history:
                self.job_history.append(job)

            # If not waiting, return immediately
            if not wait:
                return ExecutionResult(
                    job=job, success=True, metrics={"submitted": True}
                )

            # Wait for completion
            job.status = ExecutionStatus.RUNNING
            job.started_at = datetime.now()

            success = self._wait_for_completion(job)

            if success:
                job.status = ExecutionStatus.COMPLETED
                job.completed_at = datetime.now()

                if job.started_at:
                    job.execution_time_seconds = (
                        job.completed_at - job.started_at
                    ).total_seconds()

                # Collect results if configured
                results = []
                if self.config.auto_collect_results:
                    results = self._collect_results(job)
                    job.result_count = len(results)

                return ExecutionResult(
                    job=job,
                    success=True,
                    results=results,
                    metrics={
                        "execution_time": job.execution_time_seconds,
                        "result_count": job.result_count,
                    },
                )
            else:
                job.status = ExecutionStatus.FAILED
                job.completed_at = datetime.now()

                return ExecutionResult(
                    job=job, success=False, error=job.error_message or "Job failed"
                )

        except Exception as e:
            job.status = ExecutionStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()

            return ExecutionResult(job=job, success=False, error=str(e))

    def execute_batch(
        self, templates: List[AnalysisTemplate], parallel: bool = False
    ) -> List[ExecutionResult]:
        """
        Execute multiple templates.

        Args:
            templates: Templates to execute
            parallel: Whether to run in parallel (not yet implemented)

        Returns:
            List of execution results
        """
        results = []

        for i, template in enumerate(templates):
            print(f"Executing template {i+1}/{len(templates)}: {template.name}")

            result = self.execute_template(template, wait=True)
            results.append(result)

            if result.success:
                print(f"  ✓ Completed in {result.job.execution_time_seconds:.1f}s")
            else:
                print(f"  ✗ Failed: {result.error}")

        return results

    def get_job_status(self, job_id: str) -> Optional[ExecutionStatus]:
        """
        Get current status of a job.

        Args:
            job_id: Job ID to check

        Returns:
            Current execution status
        """
        # This would query the GAE API for job status
        # For now, return None (not implemented in base orchestrator)
        return None

    def _template_to_config(self, template: AnalysisTemplate) -> AnalysisConfig:
        """Convert template to AnalysisConfig for orchestrator."""
        config_dict = template.to_analysis_config()

        # Extract vertex and edge collections from template
        vertex_collections = config_dict.get("vertex_collections", [])
        edge_collections = config_dict.get("edge_collections", [])
        algorithm = config_dict.get("algorithm")

        # DEBUG LOGGING - Track collection and algorithm values
        print("\n[EXECUTOR DEBUG] Template to Config Conversion:")
        print(f"  Template name: {template.name}")
        print(
            f"  Template algorithm: {template.algorithm.algorithm.value if hasattr(template.algorithm, 'algorithm') else template.algorithm}"
        )
        print(f"  Config dict algorithm: {algorithm}")
        print(f"  Vertex collections ({len(vertex_collections)}): {vertex_collections}")
        print(f"  Edge collections ({len(edge_collections)}): {edge_collections}")

        # Fallback: try template.vertex_collections if config_dict doesn't have them
        if not vertex_collections and hasattr(template, "vertex_collections"):
            vertex_collections = template.vertex_collections
            print("  [EXECUTOR DEBUG] Using fallback vertex_collections from template")
        if not edge_collections and hasattr(template, "edge_collections"):
            edge_collections = template.edge_collections
            print("  [EXECUTOR DEBUG] Using fallback edge_collections from template")

        # Validate algorithm is present
        if not algorithm:
            raise ValueError(
                f"Template '{template.name}' has no algorithm specified! This is a critical bug."
            )

        # Create AnalysisConfig object
        # NOTE: We intentionally DON'T pass result_field here
        # Let AnalysisConfig.__post_init__ generate the standard field name
        # based on ALGORITHM_RESULT_FIELDS mapping (e.g., wcc -> "component")
        config = AnalysisConfig(
            name=config_dict["name"],
            description=template.description,
            vertex_collections=vertex_collections,
            edge_collections=edge_collections,
            algorithm=algorithm,
            algorithm_params=config_dict["params"],
            engine_size=config_dict.get("engine_size", "e16"),
            target_collection=config_dict.get(
                "result_collection", "graph_analysis_results"
            ),
            # result_field is NOT passed - will be auto-generated as standard name
        )

        # DEBUG LOGGING - Verify AnalysisConfig was created correctly
        print("[EXECUTOR DEBUG] Created AnalysisConfig:")
        print(f"  Name: {config.name}")
        print(f"  Algorithm: {config.algorithm}")
        print(
            f"  Vertex collections ({len(config.vertex_collections)}): {config.vertex_collections}"
        )
        print(
            f"  Edge collections ({len(config.edge_collections)}): {config.edge_collections}"
        )
        print(f"  Result field: {config.result_field}")
        print("[EXECUTOR DEBUG] End of conversion\n")

        return config

    def _submit_job(self, config: AnalysisConfig) -> str:
        """
        Submit job to GAE.

        Args:
            config: Analysis configuration

        Returns:
            Job ID
        """
        # Actually run the analysis using GAEOrchestrator
        result = self.orchestrator.run_analysis(config)

        # Store the result for later retrieval
        if not hasattr(self, "_analysis_results"):
            self._analysis_results = {}

        # Use the result's job_id if available, otherwise generate one
        job_id = result.job_id if result.job_id else str(__import__("uuid").uuid4())
        self._analysis_results[job_id] = result

        return job_id

    def _wait_for_completion(self, job: AnalysisJob) -> bool:
        """
        Wait for job to complete.

        Args:
            job: Job to monitor

        Returns:
            True if successful, False if failed
        """
        # Get the actual analysis result
        if (
            not hasattr(self, "_analysis_results")
            or job.job_id not in self._analysis_results
        ):
            job.error_message = "Job result not found"
            return False

        result = self._analysis_results[job.job_id]

        # Import AnalysisStatus
        from graph_analytics_ai.gae_orchestrator import AnalysisStatus

        # Check if analysis succeeded
        # CLEANING_UP means the analysis completed successfully and is just cleaning up resources
        if result.status in (AnalysisStatus.COMPLETED, AnalysisStatus.CLEANING_UP):
            # Update job with result details
            if result.duration_seconds:
                job.execution_time_seconds = result.duration_seconds
            return True
        elif result.status == AnalysisStatus.FAILED:
            job.error_message = result.error_message or "Analysis failed"
            return False
        else:
            job.error_message = f"Unexpected status: {result.status}"
            return False

    def _collect_results(self, job: AnalysisJob) -> List[Dict[str, Any]]:
        """
        Collect results from completed job.

        Args:
            job: Completed job

        Returns:
            List of result records
        """
        if not job.result_collection:
            return []

        try:
            # Get the analysis result
            if (
                hasattr(self, "_analysis_results")
                and job.job_id in self._analysis_results
            ):
                result = self._analysis_results[job.job_id]
                # Update job with result count
                if result.documents_updated:
                    job.result_count = result.documents_updated

            # Get database connection
            from ...db_connection import get_db_connection

            db = get_db_connection()

            # Check if result collection exists
            if not db.has_collection(job.result_collection):
                print(f"Warning: Result collection {job.result_collection} not found")
                return []

            # Fetch results
            collection = db.collection(job.result_collection)
            count = collection.count()

            if count == 0:
                print(f"Warning: Result collection {job.result_collection} is empty")
                return []

            # Get up to max_results
            results = list(collection.all(limit=self.config.max_results_to_fetch))

            print(f"✓ Collected {len(results)} results from {job.result_collection}")
            return results

        except Exception as e:
            # Log error but don't fail
            print(f"Warning: Could not collect results: {e}")
            return []

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get summary of all executions.

        Returns:
            Summary statistics
        """
        if not self.job_history:
            return {
                "total_jobs": 0,
                "completed": 0,
                "failed": 0,
                "avg_execution_time": 0.0,
            }

        completed = [
            j for j in self.job_history if j.status == ExecutionStatus.COMPLETED
        ]
        failed = [j for j in self.job_history if j.status == ExecutionStatus.FAILED]

        exec_times = [
            j.execution_time_seconds
            for j in completed
            if j.execution_time_seconds is not None
        ]

        return {
            "total_jobs": len(self.job_history),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": (
                len(completed) / len(self.job_history) if self.job_history else 0.0
            ),
            "avg_execution_time": (
                sum(exec_times) / len(exec_times) if exec_times else 0.0
            ),
            "total_results": sum(j.result_count or 0 for j in completed),
        }


def execute_template(template: AnalysisTemplate, wait: bool = True) -> ExecutionResult:
    """
    Convenience function to execute a single template.

    Args:
        template: Template to execute
        wait: Whether to wait for completion

    Returns:
        Execution result
    """
    executor = AnalysisExecutor()
    return executor.execute_template(template, wait=wait)
