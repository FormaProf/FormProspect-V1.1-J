"""V1.1-F2 Lot 3: pipeline, activities, reminders and history."""
from alembic import op
import sqlalchemy as sa
revision="0005_v11f2_lot3"; down_revision="0004_v11f1_lot2"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("pipeline_stages",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),
        sa.Column("name",sa.String(120),nullable=False),sa.Column("slug",sa.String(80),nullable=False),
        sa.Column("position",sa.Integer(),nullable=False),sa.Column("is_won",sa.Boolean(),nullable=False),
        sa.Column("is_lost",sa.Boolean(),nullable=False),sa.Column("is_active",sa.Boolean(),nullable=False),
        sa.Column("created_by",sa.Uuid(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()"),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.text("now()"),nullable=False),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"],["user_profiles.id"],ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_pipeline_stages_organization_id","pipeline_stages",["organization_id"])
    op.create_index("uq_pipeline_stages_org_slug","pipeline_stages",["organization_id","slug"],unique=True)
    op.create_index("ix_pipeline_stages_org_position","pipeline_stages",["organization_id","position"])
    op.create_table("prospect_stage_history",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),
        sa.Column("prospect_id",sa.Uuid(),nullable=False),sa.Column("changed_by",sa.Uuid(),nullable=False),
        sa.Column("from_stage",sa.String(80),nullable=False),sa.Column("to_stage",sa.String(80),nullable=False),
        sa.Column("note",sa.String(500),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prospect_id"],["prospects.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"],["user_profiles.id"],ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_prospect_stage_history_organization_id","prospect_stage_history",["organization_id"])
    op.create_index("ix_prospect_stage_history_prospect_id","prospect_stage_history",["prospect_id"])
    op.create_index("ix_stage_history_org_prospect_created","prospect_stage_history",["organization_id","prospect_id","created_at"])
    op.create_table("prospect_activities",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),
        sa.Column("prospect_id",sa.Uuid(),nullable=False),sa.Column("created_by",sa.Uuid(),nullable=False),
        sa.Column("assigned_to",sa.Uuid(),nullable=False),sa.Column("activity_type",sa.String(30),nullable=False),
        sa.Column("subject",sa.String(200),nullable=False),sa.Column("description",sa.Text(),nullable=False),
        sa.Column("outcome",sa.String(300),nullable=False),sa.Column("status",sa.String(30),nullable=False),
        sa.Column("priority",sa.String(20),nullable=False),sa.Column("scheduled_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("completed_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()"),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.text("now()"),nullable=False),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prospect_id"],["prospects.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"],["user_profiles.id"],ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_to"],["user_profiles.id"],ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_prospect_activities_organization_id","prospect_activities",["organization_id"])
    op.create_index("ix_prospect_activities_prospect_id","prospect_activities",["prospect_id"])
    op.create_index("ix_prospect_activities_assigned_to","prospect_activities",["assigned_to"])
    op.create_index("ix_activities_org_prospect_scheduled","prospect_activities",["organization_id","prospect_id","scheduled_at"])
    op.create_index("ix_activities_org_assigned_status","prospect_activities",["organization_id","assigned_to","status"])

def downgrade():
    op.drop_table("prospect_activities");op.drop_table("prospect_stage_history");op.drop_table("pipeline_stages")
