"""
Report generation module.

Generates HTML and PDF reports summarizing lineage data,
source coverage, and confidence metrics.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from sqlmodel import Session, func, select
from weasyprint import HTML

from app.models import Claim, Flag, Person, Source
from app.ontology import ConfidenceLevel, FlagType


class ReportGenerator:
    """Generate lineage reports in HTML and PDF formats."""

    def __init__(self, session: Session):
        self.session = session
        self.template_env = Environment(loader=FileSystemLoader("app/templates/reports"))

    def generate_summary_report(self, output_path: str, format: str = "html") -> dict:
        """
        Generate comprehensive summary report.

        Args:
            output_path: Output file path
            format: "html" or "pdf"

        Returns:
            Report metadata
        """
        # Gather statistics
        stats = self._gather_statistics()

        # Render template
        template = self.template_env.get_template("summary.html")
        html_content = template.render(
            stats=stats,
            generated_at=datetime.utcnow().isoformat(),
            title="LineageForge Summary Report",
        )

        if format == "html":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        elif format == "pdf":
            HTML(string=html_content).write_pdf(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return {
            "output_path": output_path,
            "format": format,
            "generated_at": datetime.utcnow().isoformat(),
            "stats": stats,
        }

    def _gather_statistics(self) -> dict:
        """Gather summary statistics."""
        # Person counts
        total_persons = self.session.exec(
            select(func.count(Person.person_id)).where(Person.is_active == True)
        ).one()

        # Claim counts
        total_claims = self.session.exec(
            select(func.count(Claim.claim_id)).where(Claim.is_active == True)
        ).one()

        # Confidence distribution
        confidence_distribution = {}
        for level in ConfidenceLevel:
            count = self.session.exec(
                select(func.count(Claim.claim_id))
                .where(Claim.is_active == True)
                .where(Claim.confidence_level == level)
            ).one()
            confidence_distribution[level.value] = count

        # Source counts
        source_counts = self.session.exec(
            select(Source.source_type, func.count(Source.source_id)).group_by(Source.source_type)
        ).all()

        source_distribution = {str(source_type): count for source_type, count in source_counts}

        # Flag counts
        flag_counts = self.session.exec(
            select(Flag.flag_type, func.count(Flag.flag_id))
            .where(Flag.is_resolved == False)
            .group_by(Flag.flag_type)
        ).all()

        flag_distribution = {str(flag_type): count for flag_type, count in flag_counts}
        total_flags = sum(flag_distribution.values())

        # Coverage metrics
        persons_with_birth = self.session.exec(
            select(func.count(func.distinct(Claim.subject_id)))
            .where(Claim.predicate == "born_on")
            .where(Claim.is_active == True)
        ).one()

        persons_with_death = self.session.exec(
            select(func.count(func.distinct(Claim.subject_id)))
            .where(Claim.predicate == "died_on")
            .where(Claim.is_active == True)
        ).one()

        # Notable individuals (those with external references)
        notable_count = self.session.exec(
            select(func.count(func.distinct(Person.person_id)))
            .select_from(Person)
            .join(Claim, Claim.subject_id == Person.person_id)
            .where(Person.is_active == True)
        ).one()

        return {
            "total_persons": total_persons,
            "total_claims": total_claims,
            "confidence_distribution": confidence_distribution,
            "source_distribution": source_distribution,
            "flag_distribution": flag_distribution,
            "total_flags": total_flags,
            "coverage": {
                "persons_with_birth": persons_with_birth,
                "persons_with_death": persons_with_death,
                "birth_coverage_pct": (
                    (persons_with_birth / total_persons * 100) if total_persons > 0 else 0
                ),
                "death_coverage_pct": (
                    (persons_with_death / total_persons * 100) if total_persons > 0 else 0
                ),
            },
        }

    def generate_person_report(
        self, person_id: UUID, output_path: str, format: str = "html"
    ) -> dict:
        """
        Generate detailed report for a specific person.

        Args:
            person_id: Person to report on
            output_path: Output file path
            format: "html" or "pdf"

        Returns:
            Report metadata
        """
        person = self.session.get(Person, person_id)
        if not person:
            raise ValueError(f"Person {person_id} not found")

        # Get all claims
        claims = self.session.exec(
            select(Claim)
            .where(Claim.subject_id == person_id)
            .where(Claim.is_active == True)
            .order_by(Claim.predicate, Claim.confidence.desc())
        ).all()

        # Group claims by predicate
        grouped_claims = {}
        for claim in claims:
            pred = claim.predicate.value
            if pred not in grouped_claims:
                grouped_claims[pred] = []
            grouped_claims[pred].append(claim)

        # Get flags
        flags = self.session.exec(
            select(Flag)
            .where(Flag.entity_type == "person")
            .where(Flag.entity_id == person_id)
            .where(Flag.is_resolved == False)
        ).all()

        # Render template
        template = self.template_env.get_template("person.html")
        html_content = template.render(
            person=person,
            grouped_claims=grouped_claims,
            flags=flags,
            generated_at=datetime.utcnow().isoformat(),
            title=f"Person Report: {person.canonical_name or person.person_id}",
        )

        if format == "html":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        elif format == "pdf":
            HTML(string=html_content).write_pdf(output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return {
            "person_id": str(person_id),
            "output_path": output_path,
            "format": format,
            "generated_at": datetime.utcnow().isoformat(),
            "total_claims": len(claims),
            "total_flags": len(flags),
        }
