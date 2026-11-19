"""add student_department_requests and department_id to assessment_templates

Revision ID: 5e892d11c03a
Revises: 4c18f29e1a0b
"""
from alembic import op
import sqlalchemy as sa


revision = "5e892d11c03a"
down_revision = "4c18f29e1a0b"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Add department_id to assessment_templates
    if "assessment_templates" in tables:
        cols = [c["name"] for c in inspector.get_columns("assessment_templates")]
        if "department_id" not in cols:
            with op.batch_alter_table("assessment_templates") as batch_op:
                batch_op.add_column(
                    sa.Column("department_id", sa.Integer(), nullable=True),
                )
                batch_op.create_foreign_key(
                    "fk_assessment_templates_department_id",
                    "departments",
                    ["department_id"],
                    ["id"],
                )

    # 2. Create student_department_requests table
    if "student_department_requests" not in tables:
        op.create_table(
            "student_department_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False, index=True),
            sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False, index=True),
            sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )


def downgrade():
    op.drop_table("student_department_requests")
    op.drop_column("assessment_templates", "department_id")

