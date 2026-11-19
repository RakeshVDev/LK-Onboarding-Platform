"""add user onboarding workflow columns

Revision ID: b14d9f2a8c01
Revises: a05ff5678e02
Create Date: 2026-11-13 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b14d9f2a8c01"
down_revision: Union[str, Sequence[str], None] = "a05ff5678e02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add sequential onboarding state columns to users."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("users")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}

    if "all_assessments_completed" not in existing_cols:
        op.add_column(
            "users",
            sa.Column(
                "all_assessments_completed",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )
    if "is_activated_by_admin" not in existing_cols:
        op.add_column(
            "users",
            sa.Column(
                "is_activated_by_admin",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )
    if "selected_department_id" not in existing_cols:
        op.add_column(
            "users",
            sa.Column("selected_department_id", sa.String(length=64), nullable=True),
        )
    if "department_approved" not in existing_cols:
        op.add_column(
            "users",
            sa.Column(
                "department_approved",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )
    idx_name = op.f("ix_users_selected_department_id")
    if idx_name not in existing_indexes:
        op.create_index(
            idx_name,
            "users",
            ["selected_department_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove sequential onboarding state columns from users."""
    op.drop_index(op.f("ix_users_selected_department_id"), table_name="users")
    op.drop_column("users", "department_approved")
    op.drop_column("users", "selected_department_id")
    op.drop_column("users", "is_activated_by_admin")
    op.drop_column("users", "all_assessments_completed")

