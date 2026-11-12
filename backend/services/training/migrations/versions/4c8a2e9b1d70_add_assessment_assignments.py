"""add assessment assignments table

Revision ID: 4c8a2e9b1d70
Revises: 3a91d7c4b820
Create Date: 2026-11-10 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "4c8a2e9b1d70"
down_revision = "3a91d7c4b820"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False, server_default="all"),
        sa.Column("assignment_key", sa.String(length=80), nullable=False),
        sa.Column("learner_user_id", sa.Integer(), nullable=True),
        sa.Column("cohort_id", sa.Integer(), nullable=True),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["template_id"], ["assessment_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_id"], ["cohorts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("template_id", "assignment_key", name="uq_assessment_assignment_target"),
    )
    op.create_index("ix_assessment_assignments_template_id", "assessment_assignments", ["template_id"], unique=False)
    op.create_index("ix_assessment_assignments_target_type", "assessment_assignments", ["target_type"], unique=False)
    op.create_index("ix_assessment_assignments_learner_user_id", "assessment_assignments", ["learner_user_id"], unique=False)
    op.create_index("ix_assessment_assignments_cohort_id", "assessment_assignments", ["cohort_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assessment_assignments_cohort_id", table_name="assessment_assignments")
    op.drop_index("ix_assessment_assignments_learner_user_id", table_name="assessment_assignments")
    op.drop_index("ix_assessment_assignments_target_type", table_name="assessment_assignments")
    op.drop_index("ix_assessment_assignments_template_id", table_name="assessment_assignments")
    op.drop_table("assessment_assignments")

