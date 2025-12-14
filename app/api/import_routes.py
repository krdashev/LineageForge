"""Import API endpoints."""

import tempfile
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from app.database import get_session
from app.ingestion.gedcom_importer import GedcomImporter
from app.models import Run
from app.ontology import JobStatus, JobType

router = APIRouter()


@router.post("/gedcom")
async def import_gedcom(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> dict:
    """
    Import GEDCOM file.

    Creates persons and claims. Does NOT perform identity resolution.
    """
    if not file.filename.endswith((".ged", ".gedcom")):
        raise HTTPException(status_code=400, detail="File must be a GEDCOM file (.ged or .gedcom)")

    # Create run record
    run = Run(
        job_type=JobType.IMPORT_GEDCOM,
        status=JobStatus.RUNNING,
        config={"filename": file.filename},
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ged") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Import
        importer = GedcomImporter(session)
        result = importer.import_file(tmp_file_path, file.filename)

        # Update run
        run.status = JobStatus.COMPLETED
        run.result_summary = result
        session.add(run)
        session.commit()

        return {
            "run_id": str(run.run_id),
            "status": "completed",
            "result": result,
        }

    except Exception as e:
        # Update run with error
        run.status = JobStatus.FAILED
        run.error_message = str(e)
        session.add(run)
        session.commit()

        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
