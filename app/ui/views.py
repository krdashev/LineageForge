"""UI view routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app.database import get_session
from app.models import Claim, Person, Run

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Dashboard with summary statistics."""
    # Get counts
    person_count = session.exec(
        select(func.count(Person.person_id)).where(Person.is_active == True)
    ).one()
    claim_count = session.exec(
        select(func.count(Claim.claim_id)).where(Claim.is_active == True)
    ).one()

    # Get recent runs
    recent_runs = session.exec(select(Run).order_by(Run.created_at.desc()).limit(5)).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "person_count": person_count,
            "claim_count": claim_count,
            "recent_runs": recent_runs,
        },
    )


@router.get("/tree", response_class=HTMLResponse)
async def tree_view(
    request: Request,
    person_id: UUID | None = None,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Tree visualization with Cytoscape.js."""
    root_person = None
    if person_id:
        root_person = session.get(Person, person_id)

    return templates.TemplateResponse(
        "tree.html",
        {
            "request": request,
            "root_person": root_person,
            "root_person_id": str(person_id) if person_id else None,
        },
    )


@router.get("/person/{person_id}", response_class=HTMLResponse)
async def person_detail(
    request: Request,
    person_id: UUID,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Person detail page with claims and evidence."""
    person = session.get(Person, person_id)
    if not person:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Person not found"},
            status_code=404,
        )

    # Get claims grouped by predicate
    claims = session.exec(
        select(Claim)
        .where(Claim.subject_id == person_id)
        .where(Claim.is_active == True)
        .order_by(Claim.predicate, Claim.confidence.desc())
    ).all()

    # Group claims
    grouped_claims = {}
    for claim in claims:
        pred = claim.predicate.value
        if pred not in grouped_claims:
            grouped_claims[pred] = []
        grouped_claims[pred].append(claim)

    # Detect conflicts
    conflicts = []
    for pred, pred_claims in grouped_claims.items():
        if len(pred_claims) > 1:
            values = set()
            for claim in pred_claims:
                val = claim.object_value or str(claim.object_id)
                if val:
                    values.add(val)
            if len(values) > 1:
                conflicts.append({"predicate": pred, "values": values})

    return templates.TemplateResponse(
        "person.html",
        {
            "request": request,
            "person": person,
            "grouped_claims": grouped_claims,
            "conflicts": conflicts,
        },
    )


@router.get("/runs", response_class=HTMLResponse)
async def runs_page(
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """Job runs history."""
    runs = session.exec(select(Run).order_by(Run.created_at.desc()).limit(50)).all()

    return templates.TemplateResponse(
        "runs.html",
        {
            "request": request,
            "runs": runs,
        },
    )
