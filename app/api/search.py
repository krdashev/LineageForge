"""Search API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, or_, select

from app.database import get_session
from app.models import Claim, Person
from app.ontology import PredicateType

router = APIRouter()


@router.get("")
async def search_persons(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, le=100),
    session: Session = Depends(get_session),
) -> dict:
    """
    Search for persons by name.

    Searches claims with HAS_NAME, HAS_GIVEN_NAME, and HAS_SURNAME predicates.
    """
    # Search in name claims
    name_predicates = [
        PredicateType.HAS_NAME,
        PredicateType.HAS_GIVEN_NAME,
        PredicateType.HAS_SURNAME,
    ]

    statement = (
        select(Claim)
        .where(Claim.predicate.in_(name_predicates))
        .where(Claim.is_active == True)
        .where(Claim.object_value.ilike(f"%{q}%"))
        .order_by(Claim.confidence.desc())
        .limit(limit)
    )

    claims = session.exec(statement).all()

    # Get unique persons from claims
    person_ids = list(set(claim.subject_id for claim in claims))

    # Fetch person entities
    persons_statement = select(Person).where(Person.person_id.in_(person_ids))
    persons = session.exec(persons_statement).all()

    # Build person map
    person_map = {p.person_id: p for p in persons}

    # Build results with matching claims
    results = []
    for person_id in person_ids:
        person = person_map.get(person_id)
        if not person or not person.is_active:
            continue

        matching_claims = [c for c in claims if c.subject_id == person_id]

        results.append(
            {
                "person_id": str(person.person_id),
                "canonical_name": person.canonical_name,
                "canonical_birth_year": person.canonical_birth_year,
                "canonical_death_year": person.canonical_death_year,
                "matching_claims": [
                    {
                        "predicate": claim.predicate.value,
                        "value": claim.object_value,
                        "confidence": claim.confidence,
                    }
                    for claim in matching_claims
                ],
            }
        )

    return {
        "query": q,
        "total_results": len(results),
        "results": results,
    }
