"""V1.1-A cloud identity, tenant and audit foundation."""
from alembic import op
import sqlalchemy as sa

revision = "0001_v11a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("subscription_plan", sa.String(50), nullable=False, server_default="internal"),
        sa.Column("subscription_status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("auth_user_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(40), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_user_id"),
    )
    op.create_index("ix_user_profiles_auth_user_id", "user_profiles", ["auth_user_id"], unique=True)
    op.create_index("ix_user_profiles_email", "user_profiles", ["email"])

    op.create_table(
        "organization_memberships",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(40), nullable=False, server_default="commercial"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        sa.CheckConstraint(
            "role IN ('admin','manager','commercial','trainer','admin_assistant')",
            name="ck_membership_role",
        ),
    )
    op.create_index("ix_membership_org", "organization_memberships", ["organization_id"])
    op.create_index("ix_membership_user", "organization_memberships", ["user_id"])

    op.create_table(
        "user_devices",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_fingerprint", sa.String(128), nullable=False),
        sa.Column("device_name", sa.String(160), nullable=False, server_default=""),
        sa.Column("last_ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_authorized", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "device_fingerprint", name="uq_user_device"),
    )
    op.create_index("ix_user_devices_org", "user_devices", ["organization_id"])
    op.create_index("ix_user_devices_user", "user_devices", ["user_id"])

    op.create_table(
        "audit_logs",
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("before_data", sa.JSON(), nullable=True),
        sa.Column("after_data", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=False, server_default=""),
        sa.Column("device_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(512), nullable=False, server_default=""),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_org_date", "audit_logs", ["organization_id", "occurred_at"])
    op.create_index("ix_audit_actor", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_action", "audit_logs", ["action"])
    op.create_index("ix_audit_request", "audit_logs", ["request_id"])

    # Defense in depth. The migration owner should be distinct from the runtime
    # database role; the runtime role must never receive BYPASSRLS.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION app_current_organization_id() RETURNS uuid
            LANGUAGE sql STABLE AS $$
              SELECT NULLIF(current_setting('app.organization_id', true), '')::uuid
            $$
        """)
        op.execute("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE user_devices ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
        op.execute("CREATE POLICY organizations_tenant ON organizations USING (id = app_current_organization_id())")
        op.execute("CREATE POLICY memberships_tenant ON organization_memberships USING (organization_id = app_current_organization_id()) WITH CHECK (organization_id = app_current_organization_id())")
        op.execute("CREATE POLICY devices_tenant ON user_devices USING (organization_id = app_current_organization_id()) WITH CHECK (organization_id = app_current_organization_id())")
        op.execute("CREATE POLICY audit_tenant_select ON audit_logs FOR SELECT USING (organization_id = app_current_organization_id())")
        op.execute("CREATE POLICY audit_tenant_insert ON audit_logs FOR INSERT WITH CHECK (organization_id = app_current_organization_id())")
        op.execute("""
            CREATE POLICY profiles_via_membership ON user_profiles USING (
              EXISTS (
                SELECT 1 FROM organization_memberships m
                WHERE m.user_id = user_profiles.id
                  AND m.organization_id = app_current_organization_id()
              )
            )
        """)


def downgrade() -> None:
    for table in ("audit_logs", "user_devices", "organization_memberships", "user_profiles", "organizations"):
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS app_current_organization_id()")

