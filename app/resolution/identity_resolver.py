"""
Identity resolution engine with deterministic scoring.

This module implements probabilistic entity resolution for persons,
with full auditability of merge decisions.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from app.config import settings
from app.models import Claim, MergeEvent, Person
from app.ontology import PredicateType


class IdentityResolver:
    """Resolve and merge duplicate person entities."""

    def __init__(self, session: Session, run_id: Optional[UUID] = None):
        self.session = session
        self.run_id = run_id
        self.merge_threshold = settings.identity_merge_threshold

    def resolve_all(self) -> dict:
        """
        Run identity resolution on all active persons.

        Returns summary statistics.
        """
        # Get all active persons
        persons = self.session.exec(select(Person).where(Person.is_active == True)).all()

        total_merges = 0
        total_candidates = 0

        for person in persons:
            if not person.is_active:
                continue

            # Find candidates
            candidates = self._find_candidates(person)
            total_candidates += len(candidates)

            # Score and merge
            for candidate, score in candidates:
                if score >= self.merge_threshold:
                    self._merge_persons(person, candidate, score)
                    total_merges += 1

        return {
            "persons_processed": len(persons),
            "candidates_evaluated": total_candidates,
            "merges_performed": total_merges,
        }

    def _find_candidates(self, person: Person) -> list[tuple[Person, float]]:
        """
        Find candidate persons for merging using blocking keys.

        Returns list of (candidate_person, similarity_score) tuples.
        """
        candidates = []

        # Get person's name claims
        name_claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person.person_id)
            .where(Claim.predicate == PredicateType.HAS_NAME)
            .where(Claim.is_active == True)
        ).all()

        if not name_claims:
            return candidates

        # Simple blocking: find persons with similar names
        for name_claim in name_claims:
            if not name_claim.object_value:
                continue

            name = name_claim.object_value.lower()
            name_parts = name.split()

            # Find other persons with overlapping name parts
            other_name_claims = self.session.exec(
                select(Claim)
                .where(Claim.subject_id != person.person_id)
                .where(Claim.predicate == PredicateType.HAS_NAME)
                .where(Claim.is_active == True)
            ).all()

            for other_claim in other_name_claims:
                if not other_claim.object_value:
                    continue

                other_name = other_claim.object_value.lower()
                other_parts = other_name.split()

                # Check for name overlap
                overlap = len(set(name_parts) & set(other_parts))
                if overlap >= 2:  # At least 2 name parts match
                    other_person = self.session.get(Person, other_claim.subject_id)
                    if other_person and other_person.is_active:
                        score = self._score_match(person, other_person)
                        if score > 0:
                            candidates.append((other_person, score))

        # Deduplicate and sort by score
        unique_candidates = {}
        for candidate, score in candidates:
            if candidate.person_id not in unique_candidates:
                unique_candidates[candidate.person_id] = (candidate, score)
            else:
                # Keep higher score
                if score > unique_candidates[candidate.person_id][1]:
                    unique_candidates[candidate.person_id] = (candidate, score)

        sorted_candidates = sorted(unique_candidates.values(), key=lambda x: x[1], reverse=True)

        return sorted_candidates[: settings.identity_max_candidates]

    def _score_match(self, person1: Person, person2: Person) -> float:
        """
        Score similarity between two persons.

        Returns weighted score between 0 and 1.
        """
        feature_scores = {}

        # Name similarity
        name_score = self._score_names(person1, person2)
        feature_scores["name"] = name_score

        # Date overlap
        date_score = self._score_dates(person1, person2)
        feature_scores["dates"] = date_score

        # Place similarity
        place_score = self._score_places(person1, person2)
        feature_scores["places"] = place_score

        # Relational coherence
        relation_score = self._score_relationships(person1, person2)
        feature_scores["relationships"] = relation_score

        # Weighted average
        weights = {
            "name": 0.4,
            "dates": 0.3,
            "places": 0.2,
            "relationships": 0.1,
        }

        total_score = sum(feature_scores[k] * weights[k] for k in weights)

        return total_score

    def _score_names(self, person1: Person, person2: Person) -> float:
        """Score name similarity."""
        names1 = self._get_claim_values(person1.person_id, PredicateType.HAS_NAME)
        names2 = self._get_claim_values(person2.person_id, PredicateType.HAS_NAME)

        if not names1 or not names2:
            return 0.0

        # Simple token-based similarity
        max_similarity = 0.0
        for n1 in names1:
            for n2 in names2:
                tokens1 = set(n1.lower().split())
                tokens2 = set(n2.lower().split())
                if tokens1 and tokens2:
                    jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)
                    max_similarity = max(max_similarity, jaccard)

        return max_similarity

    def _score_dates(self, person1: Person, person2: Person) -> float:
        """Score temporal overlap."""
        # Get birth dates
        birth1 = self._get_claim_values(person1.person_id, PredicateType.BORN_ON)
        birth2 = self._get_claim_values(person2.person_id, PredicateType.BORN_ON)

        # Get death dates
        death1 = self._get_claim_values(person1.person_id, PredicateType.DIED_ON)
        death2 = self._get_claim_values(person2.person_id, PredicateType.DIED_ON)

        score = 0.0
        count = 0

        # Compare birth dates
        if birth1 and birth2:
            for b1 in birth1:
                for b2 in birth2:
                    if b1 == b2:
                        score += 1.0
                        count += 1
                    # Allow some year tolerance
                    else:
                        # Simple year comparison if possible
                        score += 0.5
                        count += 1

        # Compare death dates
        if death1 and death2:
            for d1 in death1:
                for d2 in death2:
                    if d1 == d2:
                        score += 1.0
                        count += 1
                    else:
                        score += 0.5
                        count += 1

        return score / count if count > 0 else 0.5

    def _score_places(self, person1: Person, person2: Person) -> float:
        """Score geographic overlap."""
        places1 = self._get_claim_place_ids(person1.person_id)
        places2 = self._get_claim_place_ids(person2.person_id)

        if not places1 or not places2:
            return 0.5

        overlap = len(places1 & places2)
        union = len(places1 | places2)

        return overlap / union if union > 0 else 0.0

    def _score_relationships(self, person1: Person, person2: Person) -> float:
        """Score relational coherence."""
        # Get related persons
        related1 = self._get_related_persons(person1.person_id)
        related2 = self._get_related_persons(person2.person_id)

        if not related1 or not related2:
            return 0.5

        overlap = len(related1 & related2)
        return min(overlap / 2.0, 1.0)  # Normalize

    def _merge_persons(
        self, target_person: Person, source_person: Person, confidence_score: float
    ) -> None:
        """
        Merge source_person into target_person.

        All claims from source are preserved. Source person is marked inactive.
        """
        # Get feature scores for audit
        feature_scores = {
            "name": self._score_names(target_person, source_person),
            "dates": self._score_dates(target_person, source_person),
            "places": self._score_places(target_person, source_person),
            "relationships": self._score_relationships(target_person, source_person),
        }

        # Create merge event
        merge_event = MergeEvent(
            source_person_id=source_person.person_id,
            target_person_id=target_person.person_id,
            confidence_score=confidence_score,
            feature_scores=feature_scores,
            rationale=f"Automatic merge: score={confidence_score:.3f}",
            method="automatic",
            performed_by="system",
            run_id=self.run_id,
        )
        self.session.add(merge_event)

        # Mark source person as inactive
        source_person.is_active = False
        source_person.merged_into = target_person.person_id
        self.session.add(source_person)

        # Transfer claims (update subject_id)
        claims = self.session.exec(
            select(Claim).where(Claim.subject_id == source_person.person_id)
        ).all()

        for claim in claims:
            claim.subject_id = target_person.person_id
            self.session.add(claim)

        self.session.commit()

    def _get_claim_values(self, person_id: UUID, predicate: PredicateType) -> set[str]:
        """Get all claim values for a predicate."""
        claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person_id)
            .where(Claim.predicate == predicate)
            .where(Claim.is_active == True)
        ).all()

        return set(c.object_value for c in claims if c.object_value)

    def _get_claim_place_ids(self, person_id: UUID) -> set[UUID]:
        """Get all place IDs from claims."""
        claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person_id)
            .where(Claim.is_active == True)
            .where(Claim.place_id.isnot(None))
        ).all()

        return set(c.place_id for c in claims if c.place_id)

    def _get_related_persons(self, person_id: UUID) -> set[UUID]:
        """Get all related person IDs."""
        relationship_predicates = [
            PredicateType.PARENT_OF,
            PredicateType.CHILD_OF,
            PredicateType.SPOUSE_OF,
            PredicateType.SIBLING_OF,
        ]

        claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person_id)
            .where(Claim.predicate.in_(relationship_predicates))
            .where(Claim.is_active == True)
        ).all()

        return set(c.object_id for c in claims if c.object_id)
