"""outreach_opportunities, visual_assets, visibility_scores, campaigns, keyword_rankings

Revision ID: 004
Revises: 003
Create Date: 2026-05-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outreach_opportunities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("target_domain", sa.String(255), nullable=False),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("domain_authority", sa.Integer()),
        sa.Column("relevance_score", sa.Float()),
        sa.Column("status", sa.String(30), nullable=False, server_default="identified"),
        sa.Column("outreach_draft", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("replied_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outreach_opportunities_project_id", "outreach_opportunities", ["project_id"])
    op.create_index("ix_outreach_opportunities_status", "outreach_opportunities", ["status"])

    op.create_table(
        "visual_assets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "content_id",
            sa.String(),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("prompt_used", sa.Text()),
        sa.Column("model_used", sa.String(50)),
        sa.Column("storage_url", sa.String(2048)),
        sa.Column("cdn_url", sa.String(2048)),
        sa.Column("alt_text", sa.String(500)),
        sa.Column("generation_cost", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_visual_assets_content_id", "visual_assets", ["content_id"])

    op.create_table(
        "visibility_scores",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score_date", sa.Date(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("seo_quality", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ai_readability", sa.Float(), nullable=False, server_default="0"),
        sa.Column("semantic_clarity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("social_amplification", sa.Float(), nullable=False, server_default="0"),
        sa.Column("authority_signals", sa.Float(), nullable=False, server_default="0"),
        sa.Column("distribution_coverage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("raw_inputs", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "score_date", name="uq_visibility_scores_project_date"),
    )
    op.create_index("ix_visibility_scores_project_id", "visibility_scores", ["project_id"])

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("schedule_cron", sa.String(100)),
        sa.Column("target_keywords", postgresql.ARRAY(sa.String())),
        sa.Column("content_types", postgresql.ARRAY(sa.String())),
        sa.Column("publish_to_cms", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("distribute_social", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_campaigns_project_id", "campaigns", ["project_id"])

    op.create_table(
        "keyword_rankings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "keyword_id",
            sa.String(),
            sa.ForeignKey("keywords.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.Date(), nullable=False),
        sa.Column("position", sa.Integer()),
        sa.Column("url_ranking", sa.String(2048)),
        sa.Column("search_volume", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("keyword_id", "checked_at", name="uq_keyword_rankings_kw_date"),
    )
    op.create_index("ix_keyword_rankings_project_id", "keyword_rankings", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_keyword_rankings_project_id", table_name="keyword_rankings")
    op.drop_table("keyword_rankings")
    op.drop_index("ix_campaigns_project_id", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index("ix_visibility_scores_project_id", table_name="visibility_scores")
    op.drop_table("visibility_scores")
    op.drop_index("ix_visual_assets_content_id", table_name="visual_assets")
    op.drop_table("visual_assets")
    op.drop_index("ix_outreach_opportunities_status", table_name="outreach_opportunities")
    op.drop_index("ix_outreach_opportunities_project_id", table_name="outreach_opportunities")
    op.drop_table("outreach_opportunities")
