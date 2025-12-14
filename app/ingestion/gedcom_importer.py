"""
GEDCOM importer that outputs claims only.

This module parses GEDCOM files and converts all assertions into
claims with explicit provenance. It does NOT perform identity resolution.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from gedcom.element.individual import IndividualElement
from gedcom.parser import Parser
from sqlmodel import Session

from app.models import Claim, Person, Place, Source
from app.ontology import (
    ConfidenceLevel,
    PredicateType,
    SourceType,
    get_confidence_score,
)


class GedcomImporter:
    """Import GEDCOM files as claims."""

    def __init__(self, session: Session):
        self.session = session
        self.source_id: Optional[UUID] = None
        self.person_map: dict[str, UUID] = {}  # GEDCOM pointer -> person_id
        self.place_cache: dict[str, UUID] = {}  # place_name -> place_id

    def import_file(self, file_path: str, source_name: str) -> dict:
        """
        Import GEDCOM file.

        Returns summary statistics.
        """
        # Create source record
        source = Source(
            source_type=SourceType.GEDCOM_IMPORT,
            source_name=source_name,
            source_citation=f"GEDCOM file: {file_path}",
            reliability_score=0.7,  # Default for GEDCOM imports
            raw_data={"file_path": file_path},
        )
        self.session.add(source)
        self.session.commit()
        self.session.refresh(source)
        self.source_id = source.source_id

        # Parse GEDCOM
        parser = Parser()
        parser.parse_file(file_path)
        root_elements = parser.get_root_child_elements()

        # First pass: create all person entities
        individuals = [e for e in root_elements if isinstance(e, IndividualElement)]
        for individual in individuals:
            person_id = self._create_person(individual)
            self.person_map[individual.get_pointer()] = person_id

        # Second pass: extract all claims
        claim_count = 0
        for individual in individuals:
            person_id = self.person_map[individual.get_pointer()]
            claims = self._extract_claims(individual, person_id)
            for claim in claims:
                self.session.add(claim)
                claim_count += 1

        self.session.commit()

        return {
            "persons_created": len(self.person_map),
            "claims_created": claim_count,
            "source_id": str(self.source_id),
        }

    def _create_person(self, individual: IndividualElement) -> UUID:
        """Create person entity without claims."""
        person = Person()
        self.session.add(person)
        self.session.commit()
        self.session.refresh(person)
        return person.person_id

    def _extract_claims(self, individual: IndividualElement, person_id: UUID) -> list[Claim]:
        """Extract all claims from GEDCOM individual."""
        claims: list[Claim] = []

        # Names
        name_tuple = individual.get_name()
        if name_tuple and name_tuple[0]:
            full_name = f"{name_tuple[0]} {name_tuple[1]}".strip()
            claims.append(
                self._make_claim(
                    subject_id=person_id,
                    predicate=PredicateType.HAS_NAME,
                    object_value=full_name,
                    confidence=0.9,
                )
            )

            # Given name
            if name_tuple[0]:
                claims.append(
                    self._make_claim(
                        subject_id=person_id,
                        predicate=PredicateType.HAS_GIVEN_NAME,
                        object_value=name_tuple[0],
                        confidence=0.9,
                    )
                )

            # Surname
            if name_tuple[1]:
                claims.append(
                    self._make_claim(
                        subject_id=person_id,
                        predicate=PredicateType.HAS_SURNAME,
                        object_value=name_tuple[1],
                        confidence=0.9,
                    )
                )

        # Gender
        gender = individual.get_gender()
        if gender:
            claims.append(
                self._make_claim(
                    subject_id=person_id,
                    predicate=PredicateType.HAS_GENDER,
                    object_value=gender,
                    confidence=0.95,
                )
            )

        # Birth
        birth_data = individual.get_birth_data()
        if birth_data:
            birth_date = self._parse_gedcom_date(birth_data[0])
            birth_place_name = birth_data[1]

            if birth_date:
                claims.append(
                    self._make_claim(
                        subject_id=person_id,
                        predicate=PredicateType.BORN_ON,
                        object_value=birth_date.isoformat() if birth_date else None,
                        time_start=birth_date,
                        confidence=0.8,
                    )
                )

            if birth_place_name:
                place_id = self._get_or_create_place(birth_place_name)
                claims.append(
                    self._make_claim(
                        subject_id=person_id,
                        predicate=PredicateType.BORN_AT,
                        place_id=place_id,
                        confidence=0.75,
                    )
                )

        # Death
        death_data = individual.get_death_data()
        if death_data:
            death_date = self._parse_gedcom_date(death_data[0])
            death_place_name = death_data[1]

            if death_date:
                claims.append(
                    self._make_claim(
                        subject_id=person_id,
                        predicate=PredicateType.DIED_ON,
                        object_value=death_date.isoformat() if death_date else None,
                        time_start=death_date,
                        confidence=0.8,
                    )
                )

            if death_place_name:
                place_id = self._get_or_create_place(death_place_name)
                claims.append(
                    self._make_claim(
                        subject_id=person_id,
                        predicate=PredicateType.DIED_AT,
                        place_id=place_id,
                        confidence=0.75,
                    )
                )

        # Relationships - Skip for now in MVP
        # GEDCOM family relationships are complex and require parsing family records
        # For MVP, we just extract individual-level data
        # TODO: Implement family relationship parsing in future version

        return claims

    def _make_claim(
        self,
        subject_id: UUID,
        predicate: PredicateType,
        object_id: Optional[UUID] = None,
        object_value: Optional[str] = None,
        place_id: Optional[UUID] = None,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
        confidence: float = 0.5,
    ) -> Claim:
        """Create a claim with standard defaults."""
        confidence_level = ConfidenceLevel.HIGH if confidence >= 0.8 else ConfidenceLevel.MODERATE

        return Claim(
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            object_value=object_value,
            place_id=place_id,
            time_start=time_start,
            time_end=time_end,
            source_id=self.source_id,
            confidence=confidence,
            confidence_level=confidence_level,
            rationale="Imported from GEDCOM",
        )

    def _get_or_create_place(self, place_name: str) -> UUID:
        """Get or create place entity."""
        if place_name in self.place_cache:
            return self.place_cache[place_name]

        place = Place(place_name=place_name)
        self.session.add(place)
        self.session.commit()
        self.session.refresh(place)

        self.place_cache[place_name] = place.place_id
        return place.place_id

    def _parse_gedcom_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse GEDCOM date string to datetime."""
        if not date_str:
            return None

        # Simple parser - GEDCOM dates are complex, this handles basic cases
        date_str = date_str.strip().upper()

        # Remove qualifiers
        for qualifier in ["ABT", "CAL", "EST", "BEF", "AFT", "BET", "AND"]:
            date_str = date_str.replace(qualifier, "").strip()

        # Try to parse various formats
        from dateutil import parser as date_parser

        try:
            return date_parser.parse(date_str, fuzzy=True)
        except Exception:
            return None
