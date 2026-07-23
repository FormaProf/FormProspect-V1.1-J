"""V1.1-F1 Lot 2 prospect business fields and indexes."""

from alembic import op
import sqlalchemy as sa

revision = "0004_v11f1_lot2"
down_revision = "0003_v11f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prospects", sa.Column("contact_first_name", sa.String(length=100), nullable=False, server_default=""))
    op.add_column("prospects", sa.Column("contact_last_name", sa.String(length=100), nullable=False, server_default=""))
    op.add_column("prospects", sa.Column("job_title", sa.String(length=160), nullable=False, server_default=""))
    op.add_column("prospects", sa.Column("siren", sa.String(length=9), nullable=False, server_default=""))
    op.add_column("prospects", sa.Column("naf_code", sa.String(length=10), nullable=False, server_default=""))
    op.add_column("prospects", sa.Column("workforce", sa.Integer(), nullable=True))
    op.add_column("prospects", sa.Column("annual_revenue", sa.Numeric(precision=15, scale=2), nullable=True))
    op.add_column("prospects", sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"))
    op.add_column("prospects", sa.Column("next_action", sa.String(length=300), nullable=False, server_default=""))
    op.add_column("prospects", sa.Column("next_action_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_prospects_org_priority", "prospects", ["organization_id", "priority"])
    op.create_index("ix_prospects_org_next_action", "prospects", ["organization_id", "next_action_at"])


def downgrade() -> None:
    op.drop_index("ix_prospects_org_next_action", table_name="prospects")
    op.drop_index("ix_prospects_org_priority", table_name="prospects")
    op.drop_column("prospects", "next_action_at")
    op.drop_column("prospects", "next_action")
    op.drop_column("prospects", "priority")
    op.drop_column("prospects", "annual_revenue")
    op.drop_column("prospects", "workforce")
    op.drop_column("prospects", "naf_code")
    op.drop_column("prospects", "siren")
    op.drop_column("prospects", "job_title")
    op.drop_column("prospects", "contact_last_name")
    op.drop_column("prospects", "contact_first_name")
