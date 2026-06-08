"""Add public demo metadata and rate limits."""

from alembic import op
import sqlalchemy as sa


revision = "20260608_public_demo_hardening"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    campaign_columns = {column["name"] for column in inspector.get_columns("campaigns")}
    if "source" not in campaign_columns:
        op.add_column("campaigns", sa.Column("source", sa.String(length=40), nullable=False, server_default="public"))
        op.create_index("ix_campaigns_source", "campaigns", ["source"])
    if "demo_key" not in campaign_columns:
        op.add_column("campaigns", sa.Column("demo_key", sa.String(length=80), nullable=True))
        op.create_index("uq_campaigns_demo_key", "campaigns", ["demo_key"], unique=True)
    if "analysis_started_at" not in campaign_columns:
        op.add_column("campaigns", sa.Column("analysis_started_at", sa.DateTime(), nullable=True))

    if "rate_limit_events" not in inspector.get_table_names():
        op.create_table(
            "rate_limit_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("visitor_hash", sa.String(length=64), nullable=False),
            sa.Column("action", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_rate_limit_events_visitor_hash", "rate_limit_events", ["visitor_hash"])
        op.create_index("ix_rate_limit_events_action", "rate_limit_events", ["action"])
        op.create_index("ix_rate_limit_events_created_at", "rate_limit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("rate_limit_events")
    op.drop_index("uq_campaigns_demo_key", table_name="campaigns")
    op.drop_index("ix_campaigns_source", table_name="campaigns")
    op.drop_column("campaigns", "analysis_started_at")
    op.drop_column("campaigns", "demo_key")
    op.drop_column("campaigns", "source")
