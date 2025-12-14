"""API integration tests."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Claim, Person, Source
from app.ontology import ConfidenceLevel, PredicateType, SourceType


def test_health_endpoint(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_create_and_get_person(client: TestClient, session: Session):
    """Test person creation and retrieval."""
    # Create person
    person = Person(canonical_name="John Doe")
    session.add(person)
    session.commit()
    session.refresh(person)

    # Get person via API
    response = client.get(f"/api/person/{person.person_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["person_id"] == str(person.person_id)
    assert data["canonical_name"] == "John Doe"
    assert data["is_active"] is True


def test_get_person_claims(client: TestClient, session: Session):
    """Test retrieving person claims."""
    # Create person
    person = Person()
    session.add(person)
    session.commit()
    session.refresh(person)

    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create claims
    claims = [
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="John Doe",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="Jon Doe",  # Conflicting claim
            source_id=source.source_id,
            confidence=0.7,
            confidence_level=ConfidenceLevel.MODERATE,
        ),
    ]
    for claim in claims:
        session.add(claim)
    session.commit()

    # Get claims via API
    response = client.get(f"/api/person/{person.person_id}/claims")
    assert response.status_code == 200
    data = response.json()
    assert data["total_claims"] == 2
    assert "has_name" in data["claims"]
    assert len(data["claims"]["has_name"]) == 2
    assert len(data["conflicts"]) == 1  # Should detect conflict


def test_search_persons(client: TestClient, session: Session):
    """Test person search."""
    # Create person with claims
    person = Person()
    session.add(person)
    session.commit()
    session.refresh(person)

    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    claim = Claim(
        subject_id=person.person_id,
        predicate=PredicateType.HAS_NAME,
        object_value="Alice Smith",
        source_id=source.source_id,
        confidence=0.9,
        confidence_level=ConfidenceLevel.HIGH,
    )
    session.add(claim)
    session.commit()

    # Search
    response = client.get("/api/search?q=Alice")
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] >= 1
    assert any("Alice" in str(r) for r in data["results"])


def test_graph_lineage(client: TestClient, session: Session):
    """Test lineage graph generation."""
    # Create persons
    parent = Person(canonical_name="Parent")
    child = Person(canonical_name="Child")
    session.add(parent)
    session.add(child)
    session.commit()
    session.refresh(parent)
    session.refresh(child)

    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create parent-child relationship
    claim = Claim(
        subject_id=parent.person_id,
        predicate=PredicateType.PARENT_OF,
        object_id=child.person_id,
        source_id=source.source_id,
        confidence=0.9,
        confidence_level=ConfidenceLevel.HIGH,
    )
    session.add(claim)
    session.commit()

    # Get lineage graph
    response = client.get(f"/api/graph/lineage/{parent.person_id}?depth=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total_nodes"] == 2
    assert data["total_edges"] == 1
    assert len(data["edges"]) == 1
    assert data["edges"][0]["relationship"] == "parent_of"


def test_person_not_found(client: TestClient):
    """Test 404 for non-existent person."""
    from uuid import uuid4

    fake_id = uuid4()
    response = client.get(f"/api/person/{fake_id}")
    assert response.status_code == 404


def test_invalid_search_query(client: TestClient):
    """Test search with too short query."""
    response = client.get("/api/search?q=A")
    assert response.status_code == 422  # Validation error
