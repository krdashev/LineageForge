"""Person API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Claim, Person

router = APIRouter()


@router.get("/{person_id}")
async def get_person(
    person_id: UUID,
    session: Session = Depends(get_session),
) -> dict:
    """
    Get person by ID.

    Returns person entity with canonical fields.
    """
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    if not person.is_active:
        # Person was merged
        if person.merged_into:
            return {
                "person_id": str(person_id),
                "is_active": False,
                "merged_into": str(person.merged_into),
                "message": "This person was merged into another entity",
            }

    return {
        "person_id": str(person.person_id),
        "canonical_name": person.canonical_name,
        "canonical_birth_year": person.canonical_birth_year,
        "canonical_death_year": person.canonical_death_year,
        "is_active": person.is_active,
        "created_at": person.created_at.isoformat(),
        "updated_at": person.updated_at.isoformat(),
    }


@router.get("/{person_id}/claims")
async def get_person_claims(
    person_id: UUID,
    session: Session = Depends(get_session),
) -> dict:
    """
    Get all claims about a person.

    Returns claims grouped by predicate, showing conflicts and sources.
    """
    person = session.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Get all active claims
    statement = (
        select(Claim)
        .where(Claim.subject_id == person_id)
        .where(Claim.is_active == True)
        .order_by(Claim.predicate, Claim.confidence.desc())
    )
    claims = session.exec(statement).all()

    # Group by predicate
    grouped_claims = {}
    for claim in claims:
        predicate = claim.predicate.value
        if predicate not in grouped_claims:
            grouped_claims[predicate] = []

        grouped_claims[predicate].append(
            {
                "claim_id": str(claim.claim_id),
                "object_id": str(claim.object_id) if claim.object_id else None,
                "object_value": claim.object_value,
                "confidence": claim.confidence,
                "confidence_level": claim.confidence_level.value,
                "source_id": str(claim.source_id),
                "time_start": claim.time_start.isoformat() if claim.time_start else None,
                "time_end": claim.time_end.isoformat() if claim.time_end else None,
                "place_id": str(claim.place_id) if claim.place_id else None,
                "rationale": claim.rationale,
            }
        )

    # Detect conflicts (multiple claims for same predicate)
    conflicts = []
    for predicate, predicate_claims in grouped_claims.items():
        if len(predicate_claims) > 1:
            # Check if values differ
            values = set()
            for claim in predicate_claims:
                value = claim["object_value"] or claim["object_id"]
                if value:
                    values.add(value)

            if len(values) > 1:
                conflicts.append(
                    {
                        "predicate": predicate,
                        "conflicting_values": list(values),
                        "claim_count": len(predicate_claims),
                    }
                )

    return {
        "person_id": str(person_id),
        "claims": grouped_claims,
        "total_claims": len(claims),
        "conflicts": conflicts,
    }
