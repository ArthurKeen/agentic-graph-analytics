"""
Workflow tools.

Tools use a start/poll pattern so long-running agentic workflows do not
block the MCP request/response cycle:

  1. start_workflow  → returns a job_id immediately
  2. get_workflow_status(job_id) → poll until status == "completed" | "failed"
  3. list_workflow_jobs → see all jobs in the current server session
"""

import asyncio
import threading
import uuid
from typing import Any, Dict, List, Optional

from graph_analytics_ai.ai.agents import AgenticWorkflowRunner  # noqa: F401 – imported for patching
from ..server import mcp

# In-memory job registry  {job_id: {status, result, error}}
_JOBS: Dict[str, Dict[str, Any]] = {}


def _run_workflow_background(
    job_id: str,
    graph_name: str,
    input_documents: Optional[List[Dict[str, Any]]],
    max_executions: int,
    parallel: bool,
) -> None:
    """Run a workflow synchronously in a thread and update _JOBS when done."""
    try:
        from graph_analytics_ai.ai.agents import AgenticWorkflowRunner

        runner = AgenticWorkflowRunner(graph_name=graph_name, enable_tracing=False)

        if parallel:
            # run_async needs an event loop; create one for this thread
            loop = asyncio.new_event_loop()
            state = loop.run_until_complete(
                runner.run_async(
                    input_documents=input_documents,
                    max_executions=max_executions,
                    enable_parallelism=True,
                )
            )
            loop.close()
        else:
            state = runner.run(
                input_documents=input_documents,
                max_executions=max_executions,
            )

        _JOBS[job_id]["status"] = "completed"
        _JOBS[job_id]["result"] = {
            "reports": [
                {
                    "title": r.title,
                    "summary": r.summary,
                    "insight_count": len(r.insights),
                    "recommendation_count": len(r.recommendations),
                }
                for r in state.reports
            ],
            "use_case_count": len(state.use_cases),
            "execution_count": len(state.execution_results),
            "errors": state.errors,
        }
    except Exception as exc:
        _JOBS[job_id]["status"] = "failed"
        _JOBS[job_id]["error"] = str(exc)


# ---------------------------------------------------------------------------
# start_workflow
# ---------------------------------------------------------------------------
@mcp.tool()
def start_workflow(
    graph_name: str,
    max_executions: int = 3,
    parallel: bool = True,
    input_documents: Optional[List[Dict[str, Any]]] = None,
) -> dict:
    """Start an agentic graph analytics workflow in the background.

    Returns immediately with a job_id. Poll get_workflow_status(job_id)
    until the status is 'completed' or 'failed'.

    Args:
        graph_name: ArangoDB named graph to run analytics on.
        max_executions: Maximum number of analyses to execute (default 3).
        parallel: Use parallel async execution for 40-60% speedup (default True).
        input_documents: Optional list of requirement document dicts. Each dict
            should have at minimum a 'content' key with the document text.

    Returns:
        dict with keys: job_id, status ('running'), graph_name
    """
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {"status": "running", "result": None, "error": None, "graph_name": graph_name}

    thread = threading.Thread(
        target=_run_workflow_background,
        args=(job_id, graph_name, input_documents, max_executions, parallel),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "running", "graph_name": graph_name}


# ---------------------------------------------------------------------------
# get_workflow_status
# ---------------------------------------------------------------------------
@mcp.tool()
def get_workflow_status(job_id: str) -> dict:
    """Get the current status of a background workflow job.

    Args:
        job_id: The job_id returned by start_workflow.

    Returns:
        dict with keys:
          - job_id
          - status: 'running' | 'completed' | 'failed'
          - graph_name
          - result: populated when status == 'completed'
          - error: populated when status == 'failed'
    """
    if job_id not in _JOBS:
        return {"job_id": job_id, "status": "not_found", "error": f"No job with id {job_id!r}"}

    job = _JOBS[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "graph_name": job.get("graph_name"),
        "result": job.get("result"),
        "error": job.get("error"),
    }


# ---------------------------------------------------------------------------
# list_workflow_jobs
# ---------------------------------------------------------------------------
@mcp.tool()
def list_workflow_jobs() -> list:
    """List all workflow jobs in the current server session.

    Returns a list of dicts with job_id, status, and graph_name.
    Note: job history is in-memory only and resets when the server restarts.
    """
    return [
        {
            "job_id": jid,
            "status": info["status"],
            "graph_name": info.get("graph_name"),
        }
        for jid, info in _JOBS.items()
    ]
