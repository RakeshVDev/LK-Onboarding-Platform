"""add difficulty column to assessment questions and question bank

Revision ID: 4c18f29e1a0b
Revises: 3a91d7c4b820
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "4c18f29e1a0b"
down_revision = "3a91d7c4b820"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Add difficulty to assessment_questions
    if "assessment_questions" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("assessment_questions")]
        if "difficulty" not in columns:
            op.add_column(
                "assessment_questions",
                sa.Column("difficulty", sa.String(length=20), nullable=False, server_default="Medium"),
            )

    # 2. Add difficulty to assessment_question_bank
    if "assessment_question_bank" in inspector.get_table_names():
        bank_cols = [c["name"] for c in inspector.get_columns("assessment_question_bank")]
        if "difficulty" not in bank_cols:
            op.add_column(
                "assessment_question_bank",
                sa.Column("difficulty", sa.String(length=20), nullable=False, server_default="Medium"),
            )


def downgrade():
    op.drop_column("assessment_question_bank", "difficulty")
    op.drop_column("assessment_questions", "difficulty")

