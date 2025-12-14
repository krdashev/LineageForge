"""add performance indexes

Revision ID: 001_indexes
Revises:
Create Date: 2025-12-14

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_indexes"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Claims indexes for fast lookups
    op.create_index("idx_claims_subject_id", "claims", ["subject_id"])
    op.create_index("idx_claims_predicate", "claims", ["predicate"])
    op.create_index("idx_claims_source_id", "claims", ["source_id"])
    op.create_index("idx_claims_active", "claims", ["is_active"])

    # Person indexes
    op.create_index("idx_persons_active", "persons", ["is_active"])

    # Composite indexes for common queries
    op.create_index("idx_claims_subject_predicate", "claims", ["subject_id", "predicate"])
    op.create_index("idx_claims_active_predicate", "claims", ["is_active", "predicate"])

    # Flags indexes
    op.create_index("idx_flags_entity", "flags", ["entity_type", "entity_id"])
    op.create_index("idx_flags_resolved", "flags", ["is_resolved"])


def downgrade() -> None:
    op.drop_index("idx_claims_subject_id", "claims")
    op.drop_index("idx_claims_predicate", "claims")
    op.drop_index("idx_claims_source_id", "claims")
    op.drop_index("idx_claims_active", "claims")
    op.drop_index("idx_persons_active", "persons")
    op.drop_index("idx_claims_subject_predicate", "claims")
    op.drop_index("idx_claims_active_predicate", "claims")
    op.drop_index("idx_flags_entity", "flags")
    op.drop_index("idx_flags_resolved", "flags")
