"""add question sequence and metadata columns

Revision ID: 5d9c3f1a8b21
Revises: 4c8a2e9b1d70
Create Date: 2026-11-10 17:30:00.000000

"""
from collections import defaultdict
from alembic import context, op
import sqlalchemy as sa


revision = "5d9c3f1a8b21"
down_revision = "4c8a2e9b1d70"
branch_labels = None
depends_on = None


def _get_existing_columns(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def _get_existing_constraints(table_name: str) -> set[str]:
    if context.is_offline_mode():
        return set()
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    names = {uc["name"] for uc in inspector.get_unique_constraints(table_name) if uc.get("name")}
    names |= {cc["name"] for cc in inspector.get_check_constraints(table_name) if cc.get("name")}
    return names


def upgrade() -> None:
    session_cols = _get_existing_columns("assessment_sessions")
    if "expires_at" not in session_cols:
        op.add_column(
            "assessment_sessions",
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "tab_switch_count" not in session_cols:
        op.add_column(
            "assessment_sessions",
            sa.Column("tab_switch_count", sa.Integer(), nullable=False, server_default="0"),
        )

    resp_cols = _get_existing_columns("assessment_responses")
    if "is_marked_for_review" not in resp_cols:
        op.add_column(
            "assessment_responses",
            sa.Column("is_marked_for_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    aq_cols = _get_existing_columns("assessment_questions")
    with op.batch_alter_table("assessment_questions") as batch_op:
        if "difficulty" not in aq_cols:
            batch_op.add_column(
                sa.Column("difficulty", sa.String(length=20), nullable=False, server_default="Medium")
            )
        if "instructions" not in aq_cols:
            batch_op.add_column(
                sa.Column("instructions", sa.Text(), nullable=True)
            )
        if "negative_marks" not in aq_cols:
            batch_op.add_column(
                sa.Column("negative_marks", sa.Float(), nullable=False, server_default="0")
            )

    bank_cols = _get_existing_columns("assessment_question_bank")
    bank_constraints = _get_existing_constraints("assessment_question_bank")
    with op.batch_alter_table("assessment_question_bank") as batch_op:
        if "difficulty" not in bank_cols:
            batch_op.add_column(
                sa.Column("difficulty", sa.String(length=20), nullable=False, server_default="Medium")
            )
        if "instructions" not in bank_cols:
            batch_op.add_column(
                sa.Column("instructions", sa.Text(), nullable=True)
            )
        if "explanation" not in bank_cols:
            batch_op.add_column(
                sa.Column("explanation", sa.Text(), nullable=True)
            )
        if "negative_marks" not in bank_cols:
            batch_op.add_column(
                sa.Column("negative_marks", sa.Float(), nullable=False, server_default="0")
            )
        if "display_order" not in bank_cols:
            batch_op.add_column(
                sa.Column("display_order", sa.Integer(), nullable=True)
            )
        if "in_assessment" not in bank_cols:
            batch_op.add_column(
                sa.Column("in_assessment", sa.Boolean(), nullable=False, server_default=sa.true())
            )

    if not context.is_offline_mode():
        bind = op.get_bind()
        rows = bind.execute(
            sa.text(
                "SELECT id, template_id, is_active "
                "FROM assessment_question_bank "
                "ORDER BY template_id ASC, id ASC"
            )
        ).fetchall()

        counters: dict[int, int] = defaultdict(int)
        for row in rows:
            qid, template_id, is_active = row[0], row[1], bool(row[2])
            if is_active:
                counters[template_id] += 1
                bind.execute(
                    sa.text(
                        "UPDATE assessment_question_bank "
                        "SET display_order = :ord, in_assessment = :in_ass "
                        "WHERE id = :qid"
                    ),
                    {"ord": counters[template_id], "in_ass": True, "qid": qid},
                )
            else:
                bind.execute(
                    sa.text(
                        "UPDATE assessment_question_bank "
                        "SET display_order = NULL, in_assessment = :in_ass "
                        "WHERE id = :qid"
                    ),
                    {"in_ass": False, "qid": qid},
                )

    with op.batch_alter_table("assessment_question_bank") as batch_op:
        if "ck_assessment_bank_negative_marks" not in bank_constraints:
            batch_op.create_check_constraint(
                "ck_assessment_bank_negative_marks",
                "negative_marks >= 0",
            )
        if "ck_assessment_bank_order_positive" not in bank_constraints:
            batch_op.create_check_constraint(
                "ck_assessment_bank_order_positive",
                "display_order IS NULL OR display_order > 0",
            )
        if "uq_assessment_bank_template_order" not in bank_constraints:
            batch_op.create_unique_constraint(
                "uq_assessment_bank_template_order",
                ["template_id", "display_order"],
            )


def downgrade() -> None:
    bank_constraints = _get_existing_constraints("assessment_question_bank")
    bank_cols = _get_existing_columns("assessment_question_bank")
    with op.batch_alter_table("assessment_question_bank") as batch_op:
        if "uq_assessment_bank_template_order" in bank_constraints or context.is_offline_mode():
            batch_op.drop_constraint("uq_assessment_bank_template_order", type_="unique")
        if "ck_assessment_bank_order_positive" in bank_constraints or context.is_offline_mode():
            batch_op.drop_constraint("ck_assessment_bank_order_positive", type_="check")
        if "ck_assessment_bank_negative_marks" in bank_constraints or context.is_offline_mode():
            batch_op.drop_constraint("ck_assessment_bank_negative_marks", type_="check")
        if "in_assessment" in bank_cols or context.is_offline_mode():
            batch_op.drop_column("in_assessment")
        if "display_order" in bank_cols or context.is_offline_mode():
            batch_op.drop_column("display_order")
        if "negative_marks" in bank_cols or context.is_offline_mode():
            batch_op.drop_column("negative_marks")
        if "explanation" in bank_cols or context.is_offline_mode():
            batch_op.drop_column("explanation")
        if "instructions" in bank_cols or context.is_offline_mode():
            batch_op.drop_column("instructions")

    aq_cols = _get_existing_columns("assessment_questions")
    with op.batch_alter_table("assessment_questions") as batch_op:
        if "negative_marks" in aq_cols or context.is_offline_mode():
            batch_op.drop_column("negative_marks")
        if "instructions" in aq_cols or context.is_offline_mode():
            batch_op.drop_column("instructions")

