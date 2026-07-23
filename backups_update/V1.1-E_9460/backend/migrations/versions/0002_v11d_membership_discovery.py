"""V1.1-D secure organization discovery for desktop sessions."""

from alembic import op

revision = "0002_v11d"
down_revision = "0001_v11a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""
        CREATE OR REPLACE FUNCTION app_discover_memberships(p_auth_user_id uuid)
        RETURNS TABLE (
            user_id uuid,
            organization_id uuid,
            organization_name text,
            organization_slug text,
            email text,
            first_name text,
            last_name text,
            role text
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT p.id, o.id, o.name::text, o.slug::text, p.email::text,
                   p.first_name::text, p.last_name::text, m.role::text
            FROM public.user_profiles p
            JOIN public.organization_memberships m ON m.user_id = p.id
            JOIN public.organizations o ON o.id = m.organization_id
            WHERE p.auth_user_id = p_auth_user_id
              AND p.status = 'active'
              AND m.is_active = true
              AND o.status = 'active'
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION app_discover_memberships(uuid) FROM PUBLIC")
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'formaprospect_runtime') THEN
            GRANT EXECUTE ON FUNCTION app_discover_memberships(uuid) TO formaprospect_runtime;
          END IF;
        END $$
    """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS app_discover_memberships(uuid)")
