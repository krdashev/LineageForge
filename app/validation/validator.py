"""
Validation engine for detecting genealogical anomalies.

This module checks for temporal impossibilities, circular relationships,
and other logical inconsistencies. Flags are stored, not blocking.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from dateutil import parser as date_parser
from sqlmodel import Session, select

from app.models import Claim, Flag, Person
from app.ontology import FlagType, PredicateType


class Validator:
    """Validate genealogical data and generate flags."""

    def __init__(self, session: Session):
        self.session = session

    def validate_all(self) -> dict:
        """
        Run all validation rules on active data.

        Returns summary statistics.
        """
        total_flags = 0

        # Get all active persons
        persons = self.session.exec(select(Person).where(Person.is_active == True)).all()

        for person in persons:
            # Lifespan validation
            total_flags += self._validate_lifespan(person)

            # Generational spacing
            total_flags += self._validate_generational_spacing(person)

            # Temporal impossibilities
            total_flags += self._validate_temporal_consistency(person)

        # Circular relationships
        total_flags += self._detect_circular_relationships()

        # Conflicting claims
        for person in persons:
            total_flags += self._detect_conflicting_claims(person)

        return {
            "persons_validated": len(persons),
            "flags_created": total_flags,
        }

    def _validate_lifespan(self, person: Person) -> int:
        """Check for unrealistic lifespans."""
        flags_created = 0

        # Get birth and death dates
        birth_claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person.person_id)
            .where(Claim.predicate == PredicateType.BORN_ON)
            .where(Claim.is_active == True)
        ).all()

        death_claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person.person_id)
            .where(Claim.predicate == PredicateType.DIED_ON)
            .where(Claim.is_active == True)
        ).all()

        for birth_claim in birth_claims:
            birth_date = self._parse_date(birth_claim.object_value)
            if not birth_date:
                continue

            for death_claim in death_claims:
                death_date = self._parse_date(death_claim.object_value)
                if not death_date:
                    continue

                # Calculate lifespan
                lifespan_years = (death_date - birth_date).days / 365.25

                # Flag if unrealistic
                if lifespan_years < 0:
                    self._create_flag(
                        FlagType.LIFESPAN_INVALID,
                        "person",
                        person.person_id,
                        f"Death date before birth date: {lifespan_years:.1f} years",
                        severity="error",
                        details={
                            "birth_date": birth_date.isoformat(),
                            "death_date": death_date.isoformat(),
                            "lifespan_years": lifespan_years,
                        },
                    )
                    flags_created += 1

                elif lifespan_years > 120:
                    self._create_flag(
                        FlagType.LIFESPAN_INVALID,
                        "person",
                        person.person_id,
                        f"Unrealistic lifespan: {lifespan_years:.1f} years",
                        severity="warning",
                        details={
                            "birth_date": birth_date.isoformat(),
                            "death_date": death_date.isoformat(),
                            "lifespan_years": lifespan_years,
                        },
                    )
                    flags_created += 1

        return flags_created

    def _validate_generational_spacing(self, person: Person) -> int:
        """Check for unrealistic age gaps between parents and children."""
        flags_created = 0

        # Get parent relationships
        parent_claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person.person_id)
            .where(Claim.predicate == PredicateType.CHILD_OF)
            .where(Claim.is_active == True)
        ).all()

        person_birth_date = self._get_birth_date(person.person_id)
        if not person_birth_date:
            return flags_created

        for parent_claim in parent_claims:
            if not parent_claim.object_id:
                continue

            parent_birth_date = self._get_birth_date(parent_claim.object_id)
            if not parent_birth_date:
                continue

            # Calculate age gap
            age_gap_years = (person_birth_date - parent_birth_date).days / 365.25

            # Flag if unrealistic
            if age_gap_years < 10:
                self._create_flag(
                    FlagType.GENERATIONAL_SPACING_INVALID,
                    "claim",
                    parent_claim.claim_id,
                    f"Parent too young: {age_gap_years:.1f} years",
                    severity="error",
                    details={
                        "person_id": str(person.person_id),
                        "parent_id": str(parent_claim.object_id),
                        "age_gap_years": age_gap_years,
                    },
                )
                flags_created += 1

            elif age_gap_years > 60:
                self._create_flag(
                    FlagType.GENERATIONAL_SPACING_INVALID,
                    "claim",
                    parent_claim.claim_id,
                    f"Large age gap: {age_gap_years:.1f} years",
                    severity="warning",
                    details={
                        "person_id": str(person.person_id),
                        "parent_id": str(parent_claim.object_id),
                        "age_gap_years": age_gap_years,
                    },
                )
                flags_created += 1

        return flags_created

    def _validate_temporal_consistency(self, person: Person) -> int:
        """Check for events happening in wrong order."""
        flags_created = 0

        birth_date = self._get_birth_date(person.person_id)
        death_date = self._get_death_date(person.person_id)

        if not birth_date or not death_date:
            return flags_created

        # Get marriage dates
        marriage_claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person.person_id)
            .where(Claim.predicate == PredicateType.MARRIED_ON)
            .where(Claim.is_active == True)
        ).all()

        for marriage_claim in marriage_claims:
            marriage_date = self._parse_date(marriage_claim.object_value)
            if not marriage_date:
                continue

            # Marriage before birth
            if marriage_date < birth_date:
                self._create_flag(
                    FlagType.TEMPORAL_IMPOSSIBILITY,
                    "claim",
                    marriage_claim.claim_id,
                    "Marriage before birth",
                    severity="error",
                    details={
                        "person_id": str(person.person_id),
                        "marriage_date": marriage_date.isoformat(),
                        "birth_date": birth_date.isoformat(),
                    },
                )
                flags_created += 1

            # Marriage after death
            if marriage_date > death_date:
                self._create_flag(
                    FlagType.TEMPORAL_IMPOSSIBILITY,
                    "claim",
                    marriage_claim.claim_id,
                    "Marriage after death",
                    severity="error",
                    details={
                        "person_id": str(person.person_id),
                        "marriage_date": marriage_date.isoformat(),
                        "death_date": death_date.isoformat(),
                    },
                )
                flags_created += 1

        return flags_created

    def _detect_circular_relationships(self) -> int:
        """Detect circular parent-child relationships."""
        flags_created = 0

        # Get all parent-child claims
        parent_claims = self.session.exec(
            select(Claim)
            .where(Claim.predicate == PredicateType.PARENT_OF)
            .where(Claim.is_active == True)
        ).all()

        # Build adjacency list
        graph = {}
        for claim in parent_claims:
            if claim.subject_id not in graph:
                graph[claim.subject_id] = []
            if claim.object_id:
                graph[claim.subject_id].append(claim.object_id)

        # DFS to detect cycles
        visited = set()
        rec_stack = set()

        def has_cycle(node: UUID) -> bool:
            visited.add(node)
            rec_stack.add(node)

            if node in graph:
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        if has_cycle(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    self._create_flag(
                        FlagType.CIRCULAR_RELATIONSHIP,
                        "person",
                        node,
                        "Circular parent-child relationship detected",
                        severity="critical",
                        details={"node_id": str(node)},
                    )
                    flags_created += 1

        return flags_created

    def _detect_conflicting_claims(self, person: Person) -> int:
        """Detect conflicting claims for the same predicate."""
        flags_created = 0

        # Get all claims
        claims = self.session.exec(
            select(Claim).where(Claim.subject_id == person.person_id).where(Claim.is_active == True)
        ).all()

        # Group by predicate
        by_predicate = {}
        for claim in claims:
            if claim.predicate not in by_predicate:
                by_predicate[claim.predicate] = []
            by_predicate[claim.predicate].append(claim)

        # Check for conflicts
        for predicate, predicate_claims in by_predicate.items():
            if len(predicate_claims) <= 1:
                continue

            # Get unique values
            values = set()
            for claim in predicate_claims:
                value = claim.object_value or str(claim.object_id)
                if value:
                    values.add(value)

            if len(values) > 1:
                self._create_flag(
                    FlagType.CONFLICTING_CLAIMS,
                    "person",
                    person.person_id,
                    f"Conflicting claims for {predicate.value}",
                    severity="warning",
                    details={
                        "predicate": predicate.value,
                        "conflicting_values": list(values),
                        "claim_count": len(predicate_claims),
                    },
                )
                flags_created += 1

        return flags_created

    def _create_flag(
        self,
        flag_type: FlagType,
        entity_type: str,
        entity_id: UUID,
        message: str,
        severity: str = "warning",
        details: dict = None,
    ) -> None:
        """Create a validation flag."""
        flag = Flag(
            flag_type=flag_type,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            message=message,
            details=details or {},
        )
        self.session.add(flag)
        self.session.commit()

    def _get_birth_date(self, person_id: UUID) -> Optional[datetime]:
        """Get birth date for a person."""
        claim = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person_id)
            .where(Claim.predicate == PredicateType.BORN_ON)
            .where(Claim.is_active == True)
            .order_by(Claim.confidence.desc())
        ).first()

        if claim and claim.object_value:
            return self._parse_date(claim.object_value)
        return None

    def _get_death_date(self, person_id: UUID) -> Optional[datetime]:
        """Get death date for a person."""
        claim = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person_id)
            .where(Claim.predicate == PredicateType.DIED_ON)
            .where(Claim.is_active == True)
            .order_by(Claim.confidence.desc())
        ).first()

        if claim and claim.object_value:
            return self._parse_date(claim.object_value)
        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string."""
        if not date_str:
            return None

        try:
            return date_parser.parse(date_str, fuzzy=True)
        except Exception:
            return None
