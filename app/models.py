"""
Database models for LineageForge.

All models use SQLModel for type-safe ORM with Pydantic validation.
Every assertion is stored as a Claim with explicit provenance.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import JSON, Column, Field, SQLModel

from app.ontology import (
    ConfidenceLevel,
    FlagType,
    JobStatus,
    JobType,
    PredicateType,
    SourceType,
)


class Person(SQLModel, table=True):
    """
    Person entity. Identity resolution may merge multiple person records.
    """

    __tablename__ = "persons"

    person_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Canonical fields (derived from high-confidence claims)
    canonical_name: Optional[str] = None
    canonical_birth_year: Optional[int] = None
    canonical_death_year: Optional[int] = None

    # Metadata
    is_active: bool = Field(default=True)  # False if merged into another person
    merged_into: Optional[UUID] = Field(default=None, foreign_key="persons.person_id")


class Source(SQLModel, table=True):
    """
    Evidence source with full provenance tracking.
    """

    __tablename__ = "sources"

    source_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    source_type: SourceType
    source_name: str
    source_url: Optional[str] = None
    source_citation: Optional[str] = None

    # Raw source data (e.g., GEDCOM text, WikiTree JSON response)
    raw_data: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Metadata
    reliability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: Optional[str] = None


class Place(SQLModel, table=True):
    """
    Geographic location with optional hierarchical structure.
    """

    __tablename__ = "places"

    place_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    place_name: str
    place_type: Optional[str] = None  # city, county, state, country, etc.
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Hierarchical parent
    parent_place_id: Optional[UUID] = Field(default=None, foreign_key="places.place_id")

    # Standardized identifiers
    geonames_id: Optional[str] = None


class Claim(SQLModel, table=True):
    """
    Canonical claim structure. Every assertion must conform to this model.

    subject_id (person/place/event) -[predicate]-> object_id/object_value
    """

    __tablename__ = "claims"

    claim_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Core triple
    subject_id: UUID  # Usually person_id
    predicate: PredicateType
    object_id: Optional[UUID] = None  # For relationships
    object_value: Optional[str] = None  # For literal values

    # Temporal bounds
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None

    # Spatial context
    place_id: Optional[UUID] = Field(default=None, foreign_key="places.place_id")

    # Provenance
    source_id: UUID = Field(foreign_key="sources.source_id")
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    rationale: Optional[str] = None

    # Raw claim data from source
    raw_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Conflict resolution
    superseded_by: Optional[UUID] = Field(default=None, foreign_key="claims.claim_id")
    is_active: bool = Field(default=True)


class Flag(SQLModel, table=True):
    """
    Validation flags and anomaly markers.
    """

    __tablename__ = "flags"

    flag_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    flag_type: FlagType
    severity: str = Field(default="warning")  # info, warning, error, critical

    # Flagged entity
    entity_type: str  # person, claim, relationship
    entity_id: UUID

    # Description
    message: str
    details: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Resolution
    is_resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class MergeEvent(SQLModel, table=True):
    """
    Audit log for identity resolution merges.
    """

    __tablename__ = "merge_events"

    merge_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Merge participants
    source_person_id: UUID = Field(foreign_key="persons.person_id")
    target_person_id: UUID = Field(foreign_key="persons.person_id")

    # Scoring
    confidence_score: float = Field(ge=0.0, le=1.0)
    feature_scores: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Rationale
    rationale: str
    method: str = Field(default="automatic")  # automatic, manual, suggested

    # Metadata
    performed_by: Optional[str] = None  # user_id or "system"
    run_id: Optional[UUID] = Field(default=None, foreign_key="runs.run_id")


class Run(SQLModel, table=True):
    """
    Job execution tracking.
    """

    __tablename__ = "runs"

    run_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    job_type: JobType
    status: JobStatus = Field(default=JobStatus.QUEUED)

    # Configuration
    config: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Results
    result_summary: dict = Field(default_factory=dict, sa_column=Column(JSON))
    error_message: Optional[str] = None
    logs: list = Field(default_factory=list, sa_column=Column(JSON))


class ExternalRef(SQLModel, table=True):
    """
    External system references (WikiTree IDs, etc.).
    """

    __tablename__ = "external_refs"

    ref_id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    person_id: UUID = Field(foreign_key="persons.person_id")
    external_system: str  # wikitree, familysearch, findagrave, etc.
    external_id: str

    # Metadata
    verified: bool = Field(default=False)
    last_synced: Optional[datetime] = None
    sync_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
