"""add assessment intelligence tables

Revision ID: 6f9a1b2c3d4e
Revises: 5e892d11c03a, 5d9c3f1a8b21
Create Date: 2026-11-13 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f9a1b2c3d4e"
down_revision: Union[str, Sequence[str], None] = ("5e892d11c03a", "5d9c3f1a8b21")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "scoring_versions" not in existing_tables:
        op.create_table(
            "scoring_versions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("version_tag", sa.String(length=60), nullable=False),
            sa.Column("assessment_type", sa.String(length=50), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("weights_json", sa.JSON(), nullable=False),
            sa.Column("thresholds_json", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_scoring_versions_version_tag"),
            "scoring_versions",
            ["version_tag"],
            unique=True,
        )
        op.create_index(
            op.f("ix_scoring_versions_assessment_type"),
            "scoring_versions",
            ["assessment_type"],
            unique=False,
        )

    if "candidate_dimension_scores" not in existing_tables:
        op.create_table(
            "candidate_dimension_scores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("template_id", sa.Integer(), nullable=False),
            sa.Column("learner_user_id", sa.Integer(), nullable=False),
            sa.Column("scoring_version_id", sa.Integer(), nullable=True),
            sa.Column("assessment_type", sa.String(length=50), nullable=False),
            sa.Column("dimension_key", sa.String(length=100), nullable=False),
            sa.Column("dimension_label", sa.String(length=150), nullable=False),
            sa.Column("raw_score", sa.Float(), nullable=False),
            sa.Column("max_score", sa.Float(), nullable=False),
            sa.Column("normalized_score", sa.Float(), nullable=False),
            sa.Column("percentile_band", sa.String(length=50), nullable=False),
            sa.Column("evidence_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "normalized_score >= 0 AND normalized_score <= 100",
                name="ck_candidate_dim_normalized_range",
            ),
            sa.ForeignKeyConstraint(
                ["scoring_version_id"],
                ["scoring_versions.id"],
            ),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["assessment_sessions.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["template_id"],
                ["assessment_templates.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "session_id",
                "dimension_key",
                name="uq_candidate_dimension_session_key",
            ),
        )
        op.create_index(
            op.f("ix_candidate_dimension_scores_session_id"),
            "candidate_dimension_scores",
            ["session_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_candidate_dimension_scores_template_id"),
            "candidate_dimension_scores",
            ["template_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_candidate_dimension_scores_learner_user_id"),
            "candidate_dimension_scores",
            ["learner_user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_candidate_dimension_scores_scoring_version_id"),
            "candidate_dimension_scores",
            ["scoring_version_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_candidate_dimension_scores_assessment_type"),
            "candidate_dimension_scores",
            ["assessment_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_candidate_dimension_scores_dimension_key"),
            "candidate_dimension_scores",
            ["dimension_key"],
            unique=False,
        )

    if "admin_alerts" not in existing_tables:
        op.create_table(
            "admin_alerts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("template_id", sa.Integer(), nullable=True),
            sa.Column("learner_user_id", sa.Integer(), nullable=False),
            sa.Column("alert_type", sa.String(length=60), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("metrics_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("acknowledged_by_user_id", sa.Integer(), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["assessment_sessions.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["template_id"],
                ["assessment_templates.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "session_id",
                "alert_type",
                name="uq_admin_alert_session_type",
            ),
        )
        op.create_index(
            op.f("ix_admin_alerts_session_id"),
            "admin_alerts",
            ["session_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_admin_alerts_template_id"),
            "admin_alerts",
            ["template_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_admin_alerts_learner_user_id"),
            "admin_alerts",
            ["learner_user_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_admin_alerts_alert_type"),
            "admin_alerts",
            ["alert_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_admin_alerts_severity"),
            "admin_alerts",
            ["severity"],
            unique=False,
        )
        op.create_index(
            op.f("ix_admin_alerts_status"),
            "admin_alerts",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "admin_alerts" in existing_tables:
        op.drop_table("admin_alerts")
    if "candidate_dimension_scores" in existing_tables:
        op.drop_table("candidate_dimension_scores")
    if "scoring_versions" in existing_tables:
        op.drop_table("scoring_versions")

