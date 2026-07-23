"""V1.1-F1 cloud prospects foundation."""

from alembic import op
import sqlalchemy as sa

revision = "0003_v11f1"
down_revision = "0002_v11d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prospects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("contact_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("mobile", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("website", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("siret", sa.String(length=14), nullable=False, server_default=""),
        sa.Column("activity", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("address", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("postal_code", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("country", sa.String(length=120), nullable=False, server_default="France"),
        sa.Column("pipeline_stage", sa.String(length=80), nullable=False, server_default="nouveau"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("source", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["user_profiles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prospects_organization_id", "prospects", ["organization_id"])
    op.create_index("ix_prospects_owner_user_id", "prospects", ["owner_user_id"])
    op.create_index("ix_prospects_org_status", "prospects", ["organization_id", "status"])
    op.create_index(
        "ix_prospects_org_stage", "prospects", ["organization_id", "pipeline_stage"]
    )
    op.create_index("ix_prospects_org_updated", "prospects", ["organization_id", "updated_at"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE prospects ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE prospects FORCE ROW LEVEL SECURITY")
        op.execute(
            """
            CREATE POLICY prospects_tenant_policy ON prospects
            USING (
                organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid
            )
            WITH CHECK (
                organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid
            )
            """
        )
        op.execute(
            """
            DO $$ BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'formaprospect_runtime') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON prospects TO formaprospect_runtime;
              END IF;
            END $$
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS prospects_tenant_policy ON prospects")
    op.drop_index("ix_prospects_org_updated", table_name="prospects")
    op.drop_index("ix_prospects_org_stage", table_name="prospects")
    op.drop_index("ix_prospects_org_status", table_name="prospects")
    op.drop_index("ix_prospects_owner_user_id", table_name="prospects")
    op.drop_index("ix_prospects_organization_id", table_name="prospects")
    op.drop_table("prospects")
