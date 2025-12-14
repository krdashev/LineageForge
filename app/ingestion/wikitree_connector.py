"""
WikiTree API connector for lineage expansion.

This module queries WikiTree's public API and converts results to claims.
Rate limiting is enforced to respect API guidelines.
"""

import asyncio
import time
from typing import Optional
from uuid import UUID

import httpx
from sqlmodel import Session, select

from app.config import settings
from app.models import Claim, ExternalRef, Person, Place, Source
from app.ontology import (
    ConfidenceLevel,
    PredicateType,
    SourceType,
    get_confidence_score,
)


class WikiTreeConnector:
    """Connect to WikiTree API and import data as claims."""

    def __init__(self, session: Session):
        self.session = session
        self.api_base = settings.wikitree_api_base
        self.rate_limit = settings.wikitree_rate_limit
        self.last_request_time = 0.0

    async def _rate_limited_request(self, params: dict) -> dict:
        """Make rate-limited API request."""
        # Enforce rate limit
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)

        async with httpx.AsyncClient() as client:
            response = await client.get(self.api_base, params=params)
            response.raise_for_status()
            self.last_request_time = time.time()
            return response.json()

    async def get_person(self, wikitree_id: str) -> Optional[dict]:
        """
        Get person data from WikiTree.

        Args:
            wikitree_id: WikiTree ID (e.g., "Smith-12345")

        Returns:
            Person data or None if not found
        """
        params = {
            "action": "getPerson",
            "key": wikitree_id,
            "fields": "Id,Name,FirstName,LastName,BirthDate,DeathDate,BirthLocation,DeathLocation,Gender,Father,Mother,Spouses,Children",
        }

        try:
            data = await self._rate_limited_request(params)
            if data.get("status") == "0" and "person" in data:
                return data["person"][0]
            return None
        except Exception as e:
            print(f"WikiTree API error: {e}")
            return None

    async def import_person(self, wikitree_id: str) -> Optional[UUID]:
        """
        Import a person from WikiTree.

        Creates person entity, claims, and external reference.
        Returns person_id or None if import fails.
        """
        # Check if already imported
        existing_ref = self.session.exec(
            select(ExternalRef)
            .where(ExternalRef.external_system == "wikitree")
            .where(ExternalRef.external_id == wikitree_id)
        ).first()

        if existing_ref:
            return existing_ref.person_id

        # Fetch from WikiTree
        person_data = await self.get_person(wikitree_id)
        if not person_data:
            return None

        # Create source
        source = Source(
            source_type=SourceType.WIKITREE,
            source_name=f"WikiTree: {wikitree_id}",
            source_url=f"https://www.wikitree.com/wiki/{wikitree_id}",
            reliability_score=0.8,
            raw_data=person_data,
        )
        self.session.add(source)
        self.session.commit()
        self.session.refresh(source)

        # Create person
        person = Person()
        self.session.add(person)
        self.session.commit()
        self.session.refresh(person)

        # Create external reference
        ext_ref = ExternalRef(
            person_id=person.person_id,
            external_system="wikitree",
            external_id=wikitree_id,
            verified=True,
            last_synced=None,
            sync_metadata=person_data,
        )
        self.session.add(ext_ref)

        # Create claims
        claims = self._create_claims_from_wikitree(person.person_id, person_data, source.source_id)

        for claim in claims:
            self.session.add(claim)

        self.session.commit()

        return person.person_id

    def _create_claims_from_wikitree(
        self, person_id: UUID, data: dict, source_id: UUID
    ) -> list[Claim]:
        """Convert WikiTree data to claims."""
        claims = []

        # Name
        if data.get("Name"):
            claims.append(
                self._make_claim(
                    person_id,
                    PredicateType.HAS_NAME,
                    object_value=data["Name"],
                    source_id=source_id,
                    confidence=0.9,
                )
            )

        # Given name
        if data.get("FirstName"):
            claims.append(
                self._make_claim(
                    person_id,
                    PredicateType.HAS_GIVEN_NAME,
                    object_value=data["FirstName"],
                    source_id=source_id,
                    confidence=0.9,
                )
            )

        # Surname
        if data.get("LastName"):
            claims.append(
                self._make_claim(
                    person_id,
                    PredicateType.HAS_SURNAME,
                    object_value=data["LastName"],
                    source_id=source_id,
                    confidence=0.9,
                )
            )

        # Gender
        if data.get("Gender"):
            claims.append(
                self._make_claim(
                    person_id,
                    PredicateType.HAS_GENDER,
                    object_value=data["Gender"],
                    source_id=source_id,
                    confidence=0.95,
                )
            )

        # Birth date
        if data.get("BirthDate"):
            claims.append(
                self._make_claim(
                    person_id,
                    PredicateType.BORN_ON,
                    object_value=data["BirthDate"],
                    source_id=source_id,
                    confidence=0.8,
                )
            )

        # Birth place
        if data.get("BirthLocation"):
            place_id = self._get_or_create_place(data["BirthLocation"])
            claims.append(
                self._make_claim(
                    person_id,
                    PredicateType.BORN_AT,
                    place_id=place_id,
                    source_id=source_id,
                    confidence=0.75,
                )
            )

        # Death date
        if data.get("DeathDate"):
            claims.append(
                self._make_claim(
                    person_id,
                    PredicateType.DIED_ON,
                    object_value=data["DeathDate"],
                    source_id=source_id,
                    confidence=0.8,
                )
            )

        # Death place
        if data.get("DeathLocation"):
            place_id = self._get_or_create_place(data["DeathLocation"])
            claims.append(
                self._make_claim(
                    person_id,
                    PredicateType.DIED_AT,
                    place_id=place_id,
                    source_id=source_id,
                    confidence=0.75,
                )
            )

        return claims

    def _make_claim(
        self,
        subject_id: UUID,
        predicate: PredicateType,
        object_id: Optional[UUID] = None,
        object_value: Optional[str] = None,
        place_id: Optional[UUID] = None,
        source_id: UUID = None,
        confidence: float = 0.7,
    ) -> Claim:
        """Create a claim with standard defaults."""
        confidence_level = ConfidenceLevel.HIGH if confidence >= 0.8 else ConfidenceLevel.MODERATE

        return Claim(
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            object_value=object_value,
            place_id=place_id,
            source_id=source_id,
            confidence=confidence,
            confidence_level=confidence_level,
            rationale="Imported from WikiTree",
        )

    def _get_or_create_place(self, place_name: str) -> UUID:
        """Get or create place entity."""
        # Check for existing place
        place = self.session.exec(select(Place).where(Place.place_name == place_name)).first()

        if place:
            return place.place_id

        # Create new place
        place = Place(place_name=place_name)
        self.session.add(place)
        self.session.commit()
        self.session.refresh(place)

        return place.place_id

    async def expand_lineage(self, person_id: UUID, depth: int = 2, max_nodes: int = 100) -> dict:
        """
        Expand lineage from a person by following WikiTree relationships.

        Args:
            person_id: Starting person
            depth: How many generations to traverse
            max_nodes: Maximum persons to import

        Returns:
            Summary statistics
        """
        # Check if person has WikiTree reference
        ext_ref = self.session.exec(
            select(ExternalRef)
            .where(ExternalRef.person_id == person_id)
            .where(ExternalRef.external_system == "wikitree")
        ).first()

        if not ext_ref:
            return {"error": "Person has no WikiTree reference"}

        visited = set()
        queue = [(ext_ref.external_id, 0)]  # (wikitree_id, current_depth)
        imported = 0

        while queue and imported < max_nodes:
            wikitree_id, current_depth = queue.pop(0)

            if wikitree_id in visited or current_depth >= depth:
                continue

            visited.add(wikitree_id)

            # Import person
            person_id = await self.import_person(wikitree_id)
            if person_id:
                imported += 1

                # Get relationships for expansion
                person_data = await self.get_person(wikitree_id)
                if person_data and current_depth < depth - 1:
                    # Queue parents
                    if person_data.get("Father"):
                        queue.append((person_data["Father"], current_depth + 1))
                    if person_data.get("Mother"):
                        queue.append((person_data["Mother"], current_depth + 1))

            # Rate limiting
            await asyncio.sleep(self.rate_limit)

        return {
            "persons_imported": imported,
            "depth": depth,
            "max_nodes": max_nodes,
        }
