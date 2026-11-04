"""add assessment types and reusable question bank

Revision ID: 3a91d7c4b820
Revises: 0ebc47aa3f15
"""
from alembic import op
import sqlalchemy as sa

revision = "3a91d7c4b820"
down_revision = "0ebc47aa3f15"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "assessment_templates",
        sa.Column("assessment_type", sa.String(length=40), nullable=False, server_default="psychometric"),
    )
    op.create_index(
        "ix_assessment_templates_assessment_type",
        "assessment_templates",
        ["assessment_type"],
        unique=False,
    )
    op.create_table(
        "assessment_question_bank",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("question_type", sa.String(length=50), nullable=False, server_default="multiple_choice"),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("scoring_key", sa.JSON(), nullable=False),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["template_id"], ["assessment_templates.id"], ondelete="CASCADE"),
        sa.CheckConstraint("max_score > 0", name="ck_assessment_bank_max_score"),
    )
    op.create_index("ix_assessment_question_bank_template_id", "assessment_question_bank", ["template_id"])


def downgrade():
    op.drop_index("ix_assessment_question_bank_template_id", table_name="assessment_question_bank")
    op.drop_table("assessment_question_bank")
    op.drop_index("ix_assessment_templates_assessment_type", table_name="assessment_templates")
    op.drop_column("assessment_templates", "assessment_type")
