"""
LineageForge Ontology Definition v0.1.0

This module defines the formal ontology used throughout the system.
All storage, API, and UI layers must conform to these definitions.
"""

from enum import Enum
from typing import Final

ONTOLOGY_VERSION: Final[str] = "0.1.0"


class EntityType(str, Enum):
    """Core entity types in the genealogical knowledge graph."""

    PERSON = "person"
    SOURCE = "source"
    PLACE = "place"
    EVENT = "event"
    CLAIM = "claim"
    RELATIONSHIP = "relationship"


class PredicateType(str, Enum):
    """Standard predicates for genealogical claims."""

    # Identity
    HAS_NAME = "has_name"
    HAS_GIVEN_NAME = "has_given_name"
    HAS_SURNAME = "has_surname"
    HAS_GENDER = "has_gender"

    # Vital events
    BORN_ON = "born_on"
    BORN_AT = "born_at"
    DIED_ON = "died_on"
    DIED_AT = "died_at"
    MARRIED_ON = "married_on"
    MARRIED_AT = "married_at"
    BURIED_AT = "buried_at"

    # Relationships
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    SPOUSE_OF = "spouse_of"
    SIBLING_OF = "sibling_of"

    # Geographic
    RESIDED_AT = "resided_at"
    MIGRATED_FROM = "migrated_from"
    MIGRATED_TO = "migrated_to"

    # Occupational
    OCCUPATION = "occupation"

    # General
    RELATED_TO = "related_to"
    SAME_AS = "same_as"  # Identity equivalence


class SourceType(str, Enum):
    """Types of evidence sources."""

    GEDCOM_IMPORT = "gedcom_import"
    WIKITREE = "wikitree"
    EXTERNAL_DATABASE = "external_database"
    MANUAL_ENTRY = "manual_entry"
    INFERENCE = "inference"
    MERGED = "merged"


class ConfidenceLevel(str, Enum):
    """Standard confidence levels for claims."""

    DEFINITE = "definite"  # 1.0
    HIGH = "high"  # 0.8-0.99
    MODERATE = "moderate"  # 0.5-0.79
    LOW = "low"  # 0.2-0.49
    SPECULATIVE = "speculative"  # < 0.2


class FlagType(str, Enum):
    """Validation and anomaly flags."""

    LIFESPAN_INVALID = "lifespan_invalid"
    GENERATIONAL_SPACING_INVALID = "generational_spacing_invalid"
    TEMPORAL_IMPOSSIBILITY = "temporal_impossibility"
    CIRCULAR_RELATIONSHIP = "circular_relationship"
    CONFLICTING_CLAIMS = "conflicting_claims"
    MISSING_CRITICAL_DATA = "missing_critical_data"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


class JobType(str, Enum):
    """Background job types."""

    IMPORT_GEDCOM = "import_gedcom"
    RESOLVE_IDENTITIES = "resolve_identities"
    EXPAND_LINEAGE = "expand_lineage"
    VALIDATE = "validate"
    GENERATE_REPORT = "generate_report"


class JobStatus(str, Enum):
    """Job execution states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Confidence score mappings
CONFIDENCE_SCORES = {
    ConfidenceLevel.DEFINITE: 1.0,
    ConfidenceLevel.HIGH: 0.9,
    ConfidenceLevel.MODERATE: 0.65,
    ConfidenceLevel.LOW: 0.35,
    ConfidenceLevel.SPECULATIVE: 0.15,
}


def get_confidence_score(level: ConfidenceLevel) -> float:
    """Convert confidence level to numeric score."""
    return CONFIDENCE_SCORES[level]


def get_confidence_level(score: float) -> ConfidenceLevel:
    """Convert numeric score to confidence level."""
    if score >= 1.0:
        return ConfidenceLevel.DEFINITE
    elif score >= 0.8:
        return ConfidenceLevel.HIGH
    elif score >= 0.5:
        return ConfidenceLevel.MODERATE
    elif score >= 0.2:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.SPECULATIVE
