"""add user_departments table and results_cleared_at column

Revision ID: c25e0a3b9d12
Revises: b14d9f2a8c01
Create Date: 2026-11-18 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c25e0a3b9d12"
down_revision: Union[str, Sequence[str], None] = "b14d9f2a8c01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "users" in existing_tables:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "results_cleared_at" not in user_cols:
            op.add_column(
                "users",
                sa.Column("results_cleared_at", sa.DateTime(timezone=True), nullable=True),
            )

    if "user_departments" not in existing_tables:
        op.create_table(
            "user_departments",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.Column("assigned_by_user_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("user_id", "department_id", name="uq_user_department"),
        )
        op.create_index(op.f("ix_user_departments_id"), "user_departments", ["id"], unique=False)
        op.create_index(op.f("ix_user_departments_user_id"), "user_departments", ["user_id"], unique=False)
        op.create_index(op.f("ix_user_departments_department_id"), "user_departments", ["department_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "user_departments" in existing_tables:
        op.drop_table("user_departments")

    if "users" in existing_tables:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "results_cleared_at" in user_cols:
            op.drop_column("users", "results_cleared_at")
