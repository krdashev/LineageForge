"""
Background tasks for RQ worker.

All long-running operations (identity resolution, expansion, validation, reporting)
are executed as background jobs.
"""

from datetime import datetime
from uuid import UUID

from redis import Redis
from rq import Queue
from sqlmodel import Session

from app.config import settings
from app.database import engine
from app.ingestion.wikitree_connector import WikiTreeConnector
from app.models import Run
from app.ontology import JobStatus, JobType
from app.reporting.report_generator import ReportGenerator
from app.resolution.identity_resolver import IdentityResolver
from app.validation.validator import Validator

# Redis connection
redis_conn = Redis.from_url(settings.redis_url)

# RQ Queue
task_queue = Queue("lineageforge", connection=redis_conn)


def run_identity_resolution(run_id: str) -> dict:
    """
    Background task: Identity resolution.

    Args:
        run_id: Run identifier

    Returns:
        Result summary
    """
    with Session(engine) as session:
        # Update run status
        run = session.get(Run, UUID(run_id))
        if not run:
            return {"error": "Run not found"}

        run.status = JobStatus.RUNNING
        run.started_at = datetime.utcnow()
        session.add(run)
        session.commit()

        try:
            # Execute resolution
            resolver = IdentityResolver(session, run_id=UUID(run_id))
            result = resolver.resolve_all()

            # Update run
            run.status = JobStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.result_summary = result
            session.add(run)
            session.commit()

            return result

        except Exception as e:
            # Update run with error
            run.status = JobStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            session.add(run)
            session.commit()

            raise


def run_expansion(run_id: str, person_id: str, depth: int = 2, max_nodes: int = 100) -> dict:
    """
    Background task: Lineage expansion from WikiTree.

    Args:
        run_id: Run identifier
        person_id: Starting person UUID
        depth: Traversal depth
        max_nodes: Maximum persons to import

    Returns:
        Result summary
    """
    import asyncio

    with Session(engine) as session:
        # Update run status
        run = session.get(Run, UUID(run_id))
        if not run:
            return {"error": "Run not found"}

        run.status = JobStatus.RUNNING
        run.started_at = datetime.utcnow()
        session.add(run)
        session.commit()

        try:
            # Execute expansion
            connector = WikiTreeConnector(session)
            result = asyncio.run(
                connector.expand_lineage(UUID(person_id), depth=depth, max_nodes=max_nodes)
            )

            # Update run
            run.status = JobStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.result_summary = result
            session.add(run)
            session.commit()

            return result

        except Exception as e:
            # Update run with error
            run.status = JobStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            session.add(run)
            session.commit()

            raise


def run_validation(run_id: str) -> dict:
    """
    Background task: Data validation.

    Args:
        run_id: Run identifier

    Returns:
        Result summary
    """
    with Session(engine) as session:
        # Update run status
        run = session.get(Run, UUID(run_id))
        if not run:
            return {"error": "Run not found"}

        run.status = JobStatus.RUNNING
        run.started_at = datetime.utcnow()
        session.add(run)
        session.commit()

        try:
            # Execute validation
            validator = Validator(session)
            result = validator.validate_all()

            # Update run
            run.status = JobStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.result_summary = result
            session.add(run)
            session.commit()

            return result

        except Exception as e:
            # Update run with error
            run.status = JobStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            session.add(run)
            session.commit()

            raise


def generate_report(run_id: str, output_path: str, report_type: str = "summary") -> dict:
    """
    Background task: Report generation.

    Args:
        run_id: Run identifier
        output_path: Output file path
        report_type: "summary" or "person"

    Returns:
        Result summary
    """
    with Session(engine) as session:
        # Update run status
        run = session.get(Run, UUID(run_id))
        if not run:
            return {"error": "Run not found"}

        run.status = JobStatus.RUNNING
        run.started_at = datetime.utcnow()
        session.add(run)
        session.commit()

        try:
            # Generate report
            generator = ReportGenerator(session)

            if report_type == "summary":
                result = generator.generate_summary_report(output_path, format="pdf")
            else:
                return {"error": "Unsupported report type"}

            # Update run
            run.status = JobStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.result_summary = result
            session.add(run)
            session.commit()

            return result

        except Exception as e:
            # Update run with error
            run.status = JobStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            session.add(run)
            session.commit()

            raise


# Helper to enqueue tasks
def enqueue_task(task_func, *args, **kwargs):
    """Enqueue a background task."""
    job = task_queue.enqueue(task_func, *args, **kwargs, job_timeout=settings.worker_timeout)
    return job.id
