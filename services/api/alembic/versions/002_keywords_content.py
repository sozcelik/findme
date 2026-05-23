"""keywords, competitors, content tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "keywords",
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
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("search_volume", sa.Integer()),
        sa.Column("cpc", sa.Float()),
        sa.Column("keyword_difficulty", sa.Integer()),
        sa.Column("search_intent", sa.String(30)),
        sa.Column("current_position", sa.Integer()),
        sa.Column("best_position", sa.Integer()),
        sa.Column("serp_features", postgresql.JSONB()),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "keyword", name="uq_keywords_project_keyword"),
    )
    op.create_index("ix_keywords_project_id", "keywords", ["project_id"])

    op.create_table(
        "competitors",
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
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("domain_authority", sa.Integer()),
        sa.Column("backlinks_count", sa.Integer()),
        sa.Column("traffic_estimate", sa.Integer()),
        sa.Column("top_keywords", postgresql.JSONB()),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "domain", name="uq_competitors_project_domain"),
    )
    op.create_index("ix_competitors_project_id", "competitors", ["project_id"])

    op.create_table(
        "content_items",
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
        sa.Column("type", sa.String(50), nullable=False, server_default="article"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500)),
        sa.Column("body_markdown", sa.Text()),
        sa.Column("body_html", sa.Text()),
        sa.Column("meta_title", sa.String(200)),
        sa.Column("meta_description", sa.String(500)),
        sa.Column("focus_keyword", sa.String(255)),
        sa.Column("word_count", sa.Integer()),
        sa.Column("readability_score", sa.Float()),
        sa.Column("seo_score", sa.Float()),
        sa.Column("ai_visibility_score", sa.Float()),
        sa.Column("schema_markup", postgresql.JSONB()),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("campaign_id", sa.String()),
        sa.Column("ai_model_used", sa.String(50)),
        sa.Column("generation_cost", sa.Float()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_content_items_project_id", "content_items", ["project_id"])
    op.create_index("ix_content_items_org_id", "content_items", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_content_items_org_id", table_name="content_items")
    op.drop_index("ix_content_items_project_id", table_name="content_items")
    op.drop_table("content_items")
    op.drop_index("ix_competitors_project_id", table_name="competitors")
    op.drop_table("competitors")
    op.drop_index("ix_keywords_project_id", table_name="keywords")
    op.drop_table("keywords")
