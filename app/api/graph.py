"""Graph API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import Claim, Person
from app.ontology import PredicateType

router = APIRouter()

# Relationship predicates
RELATIONSHIP_PREDICATES = [
    PredicateType.PARENT_OF,
    PredicateType.CHILD_OF,
    PredicateType.SPOUSE_OF,
    PredicateType.SIBLING_OF,
]


@router.get("/lineage/{person_id}")
async def get_lineage(
    person_id: UUID,
    depth: int = Query(default=2, ge=1, le=5, description="Traversal depth"),
    session: Session = Depends(get_session),
) -> dict:
    """
    Get lineage subgraph around a person.

    Returns nodes (persons) and edges (relationships) within depth levels.
    """
    visited_persons = set()
    edges = []

    def traverse(pid: UUID, current_depth: int) -> None:
        if current_depth > depth or pid in visited_persons:
            return

        visited_persons.add(pid)

        # Get all relationship claims
        statement = (
            select(Claim)
            .where(Claim.subject_id == pid)
            .where(Claim.predicate.in_(RELATIONSHIP_PREDICATES))
            .where(Claim.is_active == True)
        )
        claims = session.exec(statement).all()

        for claim in claims:
            if claim.object_id:
                edges.append(
                    {
                        "source": str(claim.subject_id),
                        "target": str(claim.object_id),
                        "relationship": claim.predicate.value,
                        "confidence": claim.confidence,
                        "claim_id": str(claim.claim_id),
                    }
                )
                # Traverse to related person
                traverse(claim.object_id, current_depth + 1)

    # Start traversal
    traverse(person_id, 1)

    # Fetch all persons
    persons_statement = select(Person).where(Person.person_id.in_(list(visited_persons)))
    persons = session.exec(persons_statement).all()

    nodes = [
        {
            "id": str(p.person_id),
            "label": p.canonical_name or "Unknown",
            "birth_year": p.canonical_birth_year,
            "death_year": p.canonical_death_year,
            "is_root": p.person_id == person_id,
        }
        for p in persons
        if p.is_active
    ]

    return {
        "root_person_id": str(person_id),
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


@router.get("/subgraph")
async def get_subgraph(
    person_ids: str = Query(..., description="Comma-separated person IDs"),
    session: Session = Depends(get_session),
) -> dict:
    """
    Get subgraph connecting specific persons.

    Returns all relationship claims between the given persons.
    """
    # Parse person IDs
    try:
        ids = [UUID(pid.strip()) for pid in person_ids.split(",")]
    except ValueError:
        return {"error": "Invalid person IDs"}

    # Get all relationship claims between these persons
    statement = (
        select(Claim)
        .where(Claim.subject_id.in_(ids))
        .where(Claim.object_id.in_(ids))
        .where(Claim.predicate.in_(RELATIONSHIP_PREDICATES))
        .where(Claim.is_active == True)
    )
    claims = session.exec(statement).all()

    edges = [
        {
            "source": str(claim.subject_id),
            "target": str(claim.object_id),
            "relationship": claim.predicate.value,
            "confidence": claim.confidence,
            "claim_id": str(claim.claim_id),
        }
        for claim in claims
    ]

    # Fetch persons
    persons_statement = select(Person).where(Person.person_id.in_(ids))
    persons = session.exec(persons_statement).all()

    nodes = [
        {
            "id": str(p.person_id),
            "label": p.canonical_name or "Unknown",
            "birth_year": p.canonical_birth_year,
            "death_year": p.canonical_death_year,
        }
        for p in persons
        if p.is_active
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }
