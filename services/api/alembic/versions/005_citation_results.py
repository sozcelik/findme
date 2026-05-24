"""citation_results table

Revision ID: 005
Revises: 004
Create Date: 2026-05-24
"""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "citation_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("model", sa.String(50), nullable=False),  # claude, gpt-4o, perplexity
        sa.Column("mentioned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mention_position", sa.Integer(), nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),  # positive/neutral/negative/none
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("full_response", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_citation_results_project_id", "citation_results", ["project_id"])
    op.create_index("ix_citation_results_checked_at", "citation_results", ["checked_at"])


def downgrade() -> None:
    op.drop_table("citation_results")
