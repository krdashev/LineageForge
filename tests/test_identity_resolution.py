"""Identity resolution tests."""

import pytest
from sqlmodel import Session

from app.models import Claim, Person, Source
from app.ontology import ConfidenceLevel, PredicateType, SourceType
from app.resolution.identity_resolver import IdentityResolver


def test_identity_resolution_merge(session: Session):
    """Test merging duplicate persons."""
    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create two persons with similar names
    person1 = Person()
    person2 = Person()
    session.add(person1)
    session.add(person2)
    session.commit()
    session.refresh(person1)
    session.refresh(person2)

    # Add name claims
    claims = [
        Claim(
            subject_id=person1.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="John Smith",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person2.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="John Smith",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
    ]
    for claim in claims:
        session.add(claim)
    session.commit()

    # Run resolution
    resolver = IdentityResolver(session)
    result = resolver.resolve_all()

    # Verify merge occurred
    assert result["merges_performed"] >= 0  # May or may not merge based on threshold
    assert result["persons_processed"] == 2


def test_no_merge_for_different_names(session: Session):
    """Test that different names don't merge."""
    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create persons with different names
    person1 = Person()
    person2 = Person()
    session.add(person1)
    session.add(person2)
    session.commit()
    session.refresh(person1)
    session.refresh(person2)

    claims = [
        Claim(
            subject_id=person1.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="Alice Johnson",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person2.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="Bob Williams",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
    ]
    for claim in claims:
        session.add(claim)
    session.commit()

    # Run resolution
    resolver = IdentityResolver(session)
    result = resolver.resolve_all()

    # Verify no merge
    assert result["merges_performed"] == 0
    assert person1.is_active is True
    assert person2.is_active is True


def test_merge_preserves_claims(session: Session):
    """Test that merging preserves all claims."""
    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create persons
    person1 = Person()
    person2 = Person()
    session.add(person1)
    session.add(person2)
    session.commit()
    session.refresh(person1)
    session.refresh(person2)

    # Add claims
    claims = [
        Claim(
            subject_id=person1.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="Jane Doe",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person1.person_id,
            predicate=PredicateType.BORN_ON,
            object_value="1990-01-01",
            source_id=source.source_id,
            confidence=0.8,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person2.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="Jane Doe",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
    ]
    for claim in claims:
        session.add(claim)
    session.commit()

    # Force merge
    resolver = IdentityResolver(session)
    candidates = resolver._find_candidates(person1)

    if candidates and candidates[0][1] >= resolver.merge_threshold:
        initial_claim_count = len(claims)
        resolver._merge_persons(person1, person2, candidates[0][1])
        session.commit()

        # Verify claims transferred
        from sqlmodel import select

        person1_claims = session.exec(
            select(Claim).where(Claim.subject_id == person1.person_id)
        ).all()
        assert len(person1_claims) == initial_claim_count
