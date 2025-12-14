"""Validation tests."""

import pytest
from sqlmodel import Session, select

from app.models import Claim, Flag, Person, Source
from app.ontology import ConfidenceLevel, FlagType, PredicateType, SourceType
from app.validation.validator import Validator


def test_lifespan_validation_invalid(session: Session):
    """Test detection of invalid lifespan (death before birth)."""
    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create person
    person = Person()
    session.add(person)
    session.commit()
    session.refresh(person)

    # Add claims with death before birth
    claims = [
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.BORN_ON,
            object_value="1990-01-01",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.DIED_ON,
            object_value="1980-01-01",  # Before birth
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
    ]
    for claim in claims:
        session.add(claim)
    session.commit()

    # Run validation
    validator = Validator(session)
    result = validator.validate_all()

    # Check for flag
    flags = session.exec(
        select(Flag)
        .where(Flag.entity_id == person.person_id)
        .where(Flag.flag_type == FlagType.LIFESPAN_INVALID)
    ).all()

    assert len(flags) > 0
    assert flags[0].severity == "error"


def test_generational_spacing_validation(session: Session):
    """Test detection of invalid parent-child age gap."""
    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create parent and child
    parent = Person()
    child = Person()
    session.add(parent)
    session.add(child)
    session.commit()
    session.refresh(parent)
    session.refresh(child)

    # Add birth dates with small age gap
    claims = [
        Claim(
            subject_id=parent.person_id,
            predicate=PredicateType.BORN_ON,
            object_value="1990-01-01",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=child.person_id,
            predicate=PredicateType.BORN_ON,
            object_value="1995-01-01",  # Only 5 years apart
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=child.person_id,
            predicate=PredicateType.CHILD_OF,
            object_id=parent.person_id,
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
    ]
    for claim in claims:
        session.add(claim)
    session.commit()

    # Run validation
    validator = Validator(session)
    result = validator.validate_all()

    # Check for flag
    flags = session.exec(
        select(Flag).where(Flag.flag_type == FlagType.GENERATIONAL_SPACING_INVALID)
    ).all()

    assert len(flags) > 0


def test_conflicting_claims_detection(session: Session):
    """Test detection of conflicting claims."""
    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create person
    person = Person()
    session.add(person)
    session.commit()
    session.refresh(person)

    # Add conflicting name claims
    claims = [
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="John Smith",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="Jane Smith",  # Different name
            source_id=source.source_id,
            confidence=0.8,
            confidence_level=ConfidenceLevel.HIGH,
        ),
    ]
    for claim in claims:
        session.add(claim)
    session.commit()

    # Run validation
    validator = Validator(session)
    result = validator.validate_all()

    # Check for flag
    flags = session.exec(
        select(Flag)
        .where(Flag.entity_id == person.person_id)
        .where(Flag.flag_type == FlagType.CONFLICTING_CLAIMS)
    ).all()

    assert len(flags) > 0


def test_no_flags_for_valid_data(session: Session):
    """Test that valid data doesn't generate flags."""
    # Create source
    source = Source(
        source_type=SourceType.MANUAL_ENTRY,
        source_name="Test Source",
        reliability_score=0.9,
    )
    session.add(source)
    session.commit()
    session.refresh(source)

    # Create person with valid data
    person = Person()
    session.add(person)
    session.commit()
    session.refresh(person)

    claims = [
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.HAS_NAME,
            object_value="Valid Person",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.BORN_ON,
            object_value="1980-01-01",
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
        Claim(
            subject_id=person.person_id,
            predicate=PredicateType.DIED_ON,
            object_value="2020-01-01",  # Valid lifespan
            source_id=source.source_id,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
        ),
    ]
    for claim in claims:
        session.add(claim)
    session.commit()

    # Run validation
    validator = Validator(session)
    result = validator.validate_all()

    # Check no critical flags for this person
    flags = session.exec(
        select(Flag).where(Flag.entity_id == person.person_id).where(Flag.severity == "critical")
    ).all()

    assert len(flags) == 0
