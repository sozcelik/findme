"""initial tables

Revision ID: 001
Revises:
Create Date: 2026-05-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgvector")

    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(20), nullable=False, server_default="starter"),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("subscription_status", sa.String(50)),
        sa.Column("monthly_credit_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("credits_used_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "org_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "org_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website_url", sa.String(2048), nullable=False),
        sa.Column("business_description", sa.String(2000)),
        sa.Column("target_audience", sa.String(500)),
        sa.Column("industry", sa.String(100)),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("visibility_score", sa.Float()),
        sa.Column("visibility_updated_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_projects_org_id", "projects", ["org_id"])

    op.create_table(
        "agent_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "org_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("campaign_id", sa.String()),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("triggered_by", sa.String()),
        sa.Column("celery_task_id", sa.String(255)),
        sa.Column("input_data", postgresql.JSONB()),
        sa.Column("output_data", postgresql.JSONB()),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_steps", postgresql.JSONB(), server_default="[]"),
        sa.Column("error_message", sa.String()),
        sa.Column("credits_used", sa.Float()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_jobs_org_id", "agent_jobs", ["org_id"])
    op.create_index("ix_agent_jobs_project_id", "agent_jobs", ["project_id"])

    # Seed dev org so local dev works without Supabase auth
    op.execute("""
        INSERT INTO organizations (id, name, slug, plan, monthly_credit_limit)
        VALUES ('org-dev-1', 'Dev Org', 'dev', 'pro', 9999)
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("agent_jobs")
    op.drop_index("ix_projects_org_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_table("users")
    op.drop_table("organizations")
