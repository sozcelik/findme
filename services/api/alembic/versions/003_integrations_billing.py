"""cms_connections, social_connections, publish_records, social_posts

Revision ID: 003
Revises: 002
Create Date: 2026-05-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cms_connections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config_encrypted", postgresql.JSONB()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cms_connections_org_id", "cms_connections", ["org_id"])

    op.create_table(
        "social_connections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("account_name", sa.String(255)),
        sa.Column("account_id", sa.String(255)),
        sa.Column("access_token_encrypted", sa.String(2048)),
        sa.Column("refresh_token_encrypted", sa.String(2048)),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("scopes", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_social_connections_org_id", "social_connections", ["org_id"])

    op.create_table(
        "publish_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "content_id",
            sa.String(),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cms_connection_id",
            sa.String(),
            sa.ForeignKey("cms_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(255)),
        sa.Column("external_url", sa.String(2048)),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.String(1000)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_publish_records_content_id", "publish_records", ["content_id"])

    op.create_table(
        "social_posts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "content_id",
            sa.String(),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("hashtags", sa.String(500)),
        sa.Column("reddit_title", sa.String(300)),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True)),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("external_post_id", sa.String(255)),
        sa.Column("engagement", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_social_posts_content_id", "social_posts", ["content_id"])
    op.create_index("ix_social_posts_project_id", "social_posts", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_social_posts_project_id", table_name="social_posts")
    op.drop_index("ix_social_posts_content_id", table_name="social_posts")
    op.drop_table("social_posts")
    op.drop_index("ix_publish_records_content_id", table_name="publish_records")
    op.drop_table("publish_records")
    op.drop_index("ix_social_connections_org_id", table_name="social_connections")
    op.drop_table("social_connections")
    op.drop_index("ix_cms_connections_org_id", table_name="cms_connections")
    op.drop_table("cms_connections")
