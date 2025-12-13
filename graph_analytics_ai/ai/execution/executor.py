"""
GAE Analysis Executor.

Executes GAE analysis templates using the existing GAEOrchestrator.
Provides high-level interface with monitoring and result collection.
"""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from ...gae_orchestrator import GAEOrchestrator, AnalysisConfig
from ..templates.models import AnalysisTemplate
from .models import (
    AnalysisJob,
    ExecutionResult,
    ExecutionStatus,
    ExecutionConfig
)


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
        orchestrator: Optional[GAEOrchestrator] = None
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
        self,
        template: AnalysisTemplate,
        wait: bool = True
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
                "estimated_runtime": template.estimated_runtime_seconds
            }
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
                    job=job,
                    success=True,
                    metrics={"submitted": True}
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
                        "result_count": job.result_count
                    }
                )
            else:
                job.status = ExecutionStatus.FAILED
                job.completed_at = datetime.now()
                
                return ExecutionResult(
                    job=job,
                    success=False,
                    error=job.error_message or "Job failed"
                )
        
        except Exception as e:
            job.status = ExecutionStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            
            return ExecutionResult(
                job=job,
                success=False,
                error=str(e)
            )
    
    def execute_batch(
        self,
        templates: List[AnalysisTemplate],
        parallel: bool = False
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
        
        # Create AnalysisConfig object
        # Note: AnalysisConfig doesn't use 'graph' parameter, 
        # it discovers the graph from vertex/edge collections
        return AnalysisConfig(
            name=config_dict['name'],
            description=template.description,
            vertex_collections=config_dict.get('vertex_collections', []),
            edge_collections=config_dict.get('edge_collections', []),
            algorithm=config_dict['algorithm'],
            algorithm_params=config_dict['params'],
            engine_size=config_dict.get('engine_size', 'e16')
        )
    
    def _submit_job(self, config: AnalysisConfig) -> str:
        """
        Submit job to GAE.
        
        Args:
            config: Analysis configuration
            
        Returns:
            Job ID
        """
        # Use existing orchestrator to run analysis
        # For now, we'll execute synchronously
        # In future, this would submit to GAE API and return job ID
        
        # Generate a job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        return job_id
    
    def _wait_for_completion(self, job: AnalysisJob) -> bool:
        """
        Wait for job to complete.
        
        Args:
            job: Job to monitor
            
        Returns:
            True if successful, False if failed
        """
        elapsed = 0.0
        
        while elapsed < self.config.max_wait_seconds:
            # In a real implementation, this would poll GAE API
            # For now, we'll simulate immediate completion
            
            # Simulate processing time based on estimate
            if job.metadata.get('estimated_runtime'):
                time.sleep(min(
                    job.metadata['estimated_runtime'],
                    self.config.max_wait_seconds
                ))
            
            # Mark as complete
            return True
        
        # Timeout
        job.error_message = f"Job timed out after {elapsed}s"
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
            # Get database connection
            from ...db_connection import get_db_connection
            db = get_db_connection()
            
            # Check if result collection exists
            if not db.has_collection(job.result_collection):
                return []
            
            # Fetch results
            collection = db.collection(job.result_collection)
            
            # Get up to max_results
            results = list(collection.all(
                limit=self.config.max_results_to_fetch
            ))
            
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
                "avg_execution_time": 0.0
            }
        
        completed = [j for j in self.job_history if j.status == ExecutionStatus.COMPLETED]
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
            "success_rate": len(completed) / len(self.job_history) if self.job_history else 0.0,
            "avg_execution_time": sum(exec_times) / len(exec_times) if exec_times else 0.0,
            "total_results": sum(j.result_count or 0 for j in completed)
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

