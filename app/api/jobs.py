"""Jobs API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import Run
from app.ontology import JobStatus, JobType
from app.worker.tasks import enqueue_task
from app.worker.tasks import generate_report as generate_report_task
from app.worker.tasks import run_expansion as run_expansion_task
from app.worker.tasks import run_identity_resolution as run_identity_resolution_task
from app.worker.tasks import run_validation as run_validation_task

router = APIRouter()


@router.delete("/{job_id}")
async def delete_job(
    job_id: UUID,
    session: Session = Depends(get_session),
) -> dict:
    """
    Delete a job run.

    Useful for cleaning up failed jobs.
    """
    run = session.get(Run, job_id)
    if not run:
        raise HTTPException(status_code=404, detail="Job not found")

    session.delete(run)
    session.commit()

    return {"message": "Job deleted", "run_id": str(job_id)}


@router.get("/{job_id}")
async def get_job_status(
    job_id: UUID,
    session: Session = Depends(get_session),
) -> dict:
    """
    Get job status and results.

    Returns execution status, summary, and logs.
    """
    run = session.get(Run, job_id)
    if not run:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "run_id": str(run.run_id),
        "job_type": run.job_type.value,
        "status": run.status.value,
        "created_at": run.created_at.isoformat(),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "config": run.config,
        "result_summary": run.result_summary,
        "error_message": run.error_message,
        "logs": run.logs,
    }


@router.get("")
async def list_jobs(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> dict:
    """
    List recent jobs.

    Returns job history ordered by creation time.
    """
    statement = select(Run).order_by(Run.created_at.desc()).limit(limit)
    runs = session.exec(statement).all()

    return {
        "jobs": [
            {
                "run_id": str(run.run_id),
                "job_type": run.job_type.value,
                "status": run.status.value,
                "created_at": run.created_at.isoformat(),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            }
            for run in runs
        ],
        "total": len(runs),
    }


@router.post("/resolve")
async def start_identity_resolution(
    session: Session = Depends(get_session),
) -> dict:
    """
    Start identity resolution job.

    Queues background job for execution.
    """
    # Create run record
    run = Run(job_type=JobType.RESOLVE_IDENTITIES, status=JobStatus.QUEUED, config={})
    session.add(run)
    session.commit()
    session.refresh(run)

    # Enqueue task
    job_id = enqueue_task(run_identity_resolution_task, str(run.run_id))

    return {
        "run_id": str(run.run_id),
        "job_id": job_id,
        "status": "queued",
        "message": "Identity resolution job queued",
    }


@router.post("/expand")
async def start_expansion(
    person_id: UUID,
    depth: int = Query(default=2, ge=1, le=5),
    max_nodes: int = Query(default=100, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> dict:
    """
    Start lineage expansion job.

    Queues background job for WikiTree expansion.
    """
    # Create run record
    run = Run(
        job_type=JobType.EXPAND_LINEAGE,
        status=JobStatus.QUEUED,
        config={"person_id": str(person_id), "depth": depth, "max_nodes": max_nodes},
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    # Enqueue task
    job_id = enqueue_task(run_expansion_task, str(run.run_id), str(person_id), depth, max_nodes)

    return {
        "run_id": str(run.run_id),
        "job_id": job_id,
        "status": "queued",
        "message": "Lineage expansion job queued",
    }


@router.post("/validate")
async def start_validation(
    session: Session = Depends(get_session),
) -> dict:
    """
    Start validation job.

    Queues background job for data validation.
    """
    # Create run record
    run = Run(job_type=JobType.VALIDATE, status=JobStatus.QUEUED, config={})
    session.add(run)
    session.commit()
    session.refresh(run)

    # Enqueue task
    job_id = enqueue_task(run_validation_task, str(run.run_id))

    return {
        "run_id": str(run.run_id),
        "job_id": job_id,
        "status": "queued",
        "message": "Validation job queued",
    }


@router.post("/report")
async def generate_report(
    output_path: str = Query(default="/tmp/report.pdf"),
    session: Session = Depends(get_session),
) -> dict:
    """
    Generate report job.

    Queues background job for report generation.
    """
    # Create run record
    run = Run(
        job_type=JobType.GENERATE_REPORT,
        status=JobStatus.QUEUED,
        config={"output_path": output_path},
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    # Enqueue task
    job_id = enqueue_task(generate_report_task, str(run.run_id), output_path)

    return {
        "run_id": str(run.run_id),
        "job_id": job_id,
        "status": "queued",
        "message": "Report generation job queued",
    }
