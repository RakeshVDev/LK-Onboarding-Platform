"""add cohort workspace tables and all startup-only training schema additions

Revision ID: 7a0b2c4d8e91
Revises: 6f9a1b2c3d4e
Create Date: 2026-11-18 09:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a0b2c4d8e91"
down_revision: Union[str, Sequence[str], None] = "6f9a1b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(inspector, table_name: str) -> set[str]:
    return {c["name"] for c in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Columns previously applied via startup auto-migration
    if "cohorts" in existing_tables:
        cohorts_cols = _cols(inspector, "cohorts")
        if "course_id" not in cohorts_cols:
            op.add_column("cohorts", sa.Column("course_id", sa.Integer(), nullable=True))
            op.create_index("ix_cohorts_course_id", "cohorts", ["course_id"], unique=False)

    if "assessment_templates" in existing_tables:
        tpl_cols = _cols(inspector, "assessment_templates")
        if "assessment_tag" not in tpl_cols:
            op.add_column(
                "assessment_templates",
                sa.Column("assessment_tag", sa.String(length=40), server_default="Assessment", nullable=False),
            )
        if "custom_tags" not in tpl_cols:
            op.add_column("assessment_templates", sa.Column("custom_tags", sa.JSON(), nullable=True))
        if "reading_passage" not in tpl_cols:
            op.add_column("assessment_templates", sa.Column("reading_passage", sa.Text(), nullable=True))
        if "due_at" not in tpl_cols:
            op.add_column("assessment_templates", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))

    if "assessment_sessions" in existing_tables:
        sess_cols = _cols(inspector, "assessment_sessions")
        if "assigned_set" not in sess_cols:
            op.add_column(
                "assessment_sessions",
                sa.Column("assigned_set", sa.String(length=10), server_default="A", nullable=False),
            )
        if "template_name_snapshot" not in sess_cols:
            op.add_column(
                "assessment_sessions",
                sa.Column("template_name_snapshot", sa.String(length=200), nullable=True),
            )
        if "assessment_type_snapshot" not in sess_cols:
            op.add_column(
                "assessment_sessions",
                sa.Column("assessment_type_snapshot", sa.String(length=40), nullable=True),
            )
        if "assessment_tag_snapshot" not in sess_cols:
            op.add_column(
                "assessment_sessions",
                sa.Column("assessment_tag_snapshot", sa.String(length=40), nullable=True),
            )
        if "department_id_snapshot" not in sess_cols:
            op.add_column(
                "assessment_sessions",
                sa.Column("department_id_snapshot", sa.Integer(), nullable=True),
            )

    if "assessment_questions" in existing_tables:
        aq_cols = _cols(inspector, "assessment_questions")
        if "question_set" not in aq_cols:
            op.add_column(
                "assessment_questions",
                sa.Column("question_set", sa.String(length=10), server_default="A", nullable=False),
            )
        if "passage_text" not in aq_cols:
            op.add_column("assessment_questions", sa.Column("passage_text", sa.Text(), nullable=True))

    if "assessment_question_bank" in existing_tables:
        qb_cols = _cols(inspector, "assessment_question_bank")
        if "question_set" not in qb_cols:
            op.add_column(
                "assessment_question_bank",
                sa.Column("question_set", sa.String(length=10), server_default="A", nullable=False),
            )
        if "passage_text" not in qb_cols:
            op.add_column("assessment_question_bank", sa.Column("passage_text", sa.Text(), nullable=True))

    # 2. Existing training/live-class tables not yet in Alembic
    if "cohort_teachers" not in existing_tables:
        op.create_table(
            "cohort_teachers",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cohort_id", sa.Integer(), sa.ForeignKey("cohorts.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("assigned_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("cohort_id", "user_id", name="uq_cohort_teacher"),
        )
        op.create_index("ix_cohort_teachers_cohort_id", "cohort_teachers", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_teachers_user_id", "cohort_teachers", ["user_id"], unique=False)

    if "cohort_material_deliveries" not in existing_tables:
        op.create_table(
            "cohort_material_deliveries",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cohort_id", sa.Integer(), sa.ForeignKey("cohorts.id"), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("material_id", sa.Integer(), sa.ForeignKey("learning_materials.id"), nullable=False),
            sa.Column("sent_by_user_id", sa.Integer(), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("cohort_id", "material_id", name="uq_cohort_material_delivery"),
        )
        op.create_index("ix_cohort_material_deliveries_cohort_id", "cohort_material_deliveries", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_material_deliveries_course_id", "cohort_material_deliveries", ["course_id"], unique=False)
        op.create_index("ix_cohort_material_deliveries_material_id", "cohort_material_deliveries", ["material_id"], unique=False)
        op.create_index("ix_cohort_material_deliveries_sent_by_user_id", "cohort_material_deliveries", ["sent_by_user_id"], unique=False)

    if "department_course_deletion_requests" not in existing_tables:
        op.create_table(
            "department_course_deletion_requests",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.Column("department_name", sa.String(length=150), nullable=False),
            sa.Column("course_id", sa.Integer(), nullable=True),
            sa.Column("target_type", sa.String(length=30), nullable=False),
            sa.Column("initiated_by_user_id", sa.Integer(), nullable=False),
            sa.Column("approved_by_user_ids_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_dept_course_del_req_dept_id", "department_course_deletion_requests", ["department_id"], unique=False)
        op.create_index("ix_dept_course_del_req_status", "department_course_deletion_requests", ["status"], unique=False)

    if "live_class_sessions" not in existing_tables:
        op.create_table(
            "live_class_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
            sa.Column("instructor_user_id", sa.Integer(), nullable=False),
            sa.Column("instructor_name", sa.String(length=150), nullable=True),
            sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), server_default="60", nullable=False),
            sa.Column("meeting_url", sa.String(length=500), nullable=False),
            sa.Column("platform", sa.String(length=60), server_default="Video Call", nullable=False),
            sa.Column("status", sa.String(length=30), server_default="scheduled", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_live_class_sessions_department_id", "live_class_sessions", ["department_id"], unique=False)
        op.create_index("ix_live_class_sessions_instructor_user_id", "live_class_sessions", ["instructor_user_id"], unique=False)
        op.create_index("ix_live_class_sessions_status", "live_class_sessions", ["status"], unique=False)

    # 3. Persistent Cohort Workspace tables (replacing browser localStorage)
    if "cohort_chapters" not in existing_tables:
        op.create_table(
            "cohort_chapters",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cohort_id", sa.Integer(), nullable=True),
            sa.Column("department_id", sa.Integer(), nullable=True),
            sa.Column("department_name", sa.String(length=150), server_default="All / Common", nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("sequence_order", sa.Integer(), server_default="1", nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_cohort_chapters_cohort_id", "cohort_chapters", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_chapters_department_id", "cohort_chapters", ["department_id"], unique=False)

    if "cohort_lessons" not in existing_tables:
        op.create_table(
            "cohort_lessons",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("cohort_chapters.id", ondelete="CASCADE"), nullable=False),
            sa.Column("cohort_id", sa.Integer(), nullable=True),
            sa.Column("department_id", sa.Integer(), nullable=True),
            sa.Column("department_name", sa.String(length=150), server_default="All / Common", nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("lesson_type", sa.String(length=30), nullable=False),
            sa.Column("duration", sa.String(length=60), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("video_url", sa.String(length=1000), nullable=True),
            sa.Column("text_notes", sa.Text(), nullable=True),
            sa.Column("download_url", sa.Text(), nullable=True),
            sa.Column("file_size", sa.String(length=60), nullable=True),
            sa.Column("file_name", sa.String(length=255), nullable=True),
            sa.Column("quiz_questions_count", sa.Integer(), nullable=True),
            sa.Column("is_published", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("scheduled_date", sa.String(length=80), nullable=True),
            sa.Column("scheduled_time", sa.String(length=80), nullable=True),
            sa.Column("meeting_url", sa.String(length=500), nullable=True),
            sa.Column("is_live_now", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("trainer_name", sa.String(length=150), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_cohort_lessons_chapter_id", "cohort_lessons", ["chapter_id"], unique=False)
        op.create_index("ix_cohort_lessons_cohort_id", "cohort_lessons", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_lessons_department_id", "cohort_lessons", ["department_id"], unique=False)

    if "cohort_assignments" not in existing_tables:
        op.create_table(
            "cohort_assignments",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cohort_id", sa.Integer(), nullable=True),
            sa.Column("department_id", sa.Integer(), nullable=True),
            sa.Column("department_name", sa.String(length=150), server_default="All / Common", nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("module", sa.String(length=255), server_default="", nullable=False),
            sa.Column("description", sa.Text(), server_default="", nullable=False),
            sa.Column("points", sa.Integer(), server_default="100", nullable=False),
            sa.Column("due_date", sa.String(length=80), server_default="", nullable=False),
            sa.Column("requirements_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("attachment_name", sa.String(length=255), nullable=True),
            sa.Column("attachment_url", sa.Text(), nullable=True),
            sa.Column("attachment_size", sa.String(length=60), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_cohort_assignments_cohort_id", "cohort_assignments", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_assignments_department_id", "cohort_assignments", ["department_id"], unique=False)

    if "cohort_assignment_submissions" not in existing_tables:
        op.create_table(
            "cohort_assignment_submissions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("cohort_assignments.id", ondelete="CASCADE"), nullable=False),
            sa.Column("learner_user_id", sa.Integer(), nullable=False),
            sa.Column("learner_name", sa.String(length=150), nullable=False),
            sa.Column("learner_email", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=30), server_default="submitted", nullable=False),
            sa.Column("submission_url", sa.String(length=1000), nullable=False),
            sa.Column("submission_notes", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=True),
            sa.Column("trainer_feedback", sa.Text(), nullable=True),
            sa.Column("graded_by_user_id", sa.Integer(), nullable=True),
            sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("assignment_id", "learner_user_id", name="uq_cohort_assignment_submission"),
        )
        op.create_index("ix_cohort_assignment_submissions_assignment_id", "cohort_assignment_submissions", ["assignment_id"], unique=False)
        op.create_index("ix_cohort_assignment_submissions_learner_user_id", "cohort_assignment_submissions", ["learner_user_id"], unique=False)

    if "cohort_quizzes" not in existing_tables:
        op.create_table(
            "cohort_quizzes",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cohort_id", sa.Integer(), nullable=True),
            sa.Column("department_id", sa.Integer(), nullable=True),
            sa.Column("department_name", sa.String(length=150), server_default="All / Common", nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("module", sa.String(length=255), server_default="", nullable=False),
            sa.Column("questions_count", sa.Integer(), server_default="5", nullable=False),
            sa.Column("duration_minutes", sa.Integer(), server_default="15", nullable=False),
            sa.Column("due_date", sa.String(length=80), server_default="", nullable=False),
            sa.Column("passing_score", sa.Integer(), server_default="70", nullable=False),
            sa.Column("attachment_name", sa.String(length=255), nullable=True),
            sa.Column("attachment_url", sa.Text(), nullable=True),
            sa.Column("attachment_size", sa.String(length=60), nullable=True),
            sa.Column("questions_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_cohort_quizzes_cohort_id", "cohort_quizzes", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_quizzes_department_id", "cohort_quizzes", ["department_id"], unique=False)

    if "cohort_quiz_submissions" not in existing_tables:
        op.create_table(
            "cohort_quiz_submissions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("cohort_quizzes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("learner_user_id", sa.Integer(), nullable=False),
            sa.Column("learner_name", sa.String(length=150), nullable=False),
            sa.Column("learner_email", sa.String(length=255), nullable=True),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("passed", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("answers_json", sa.Text(), server_default="{}", nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("quiz_id", "learner_user_id", name="uq_cohort_quiz_submission"),
        )
        op.create_index("ix_cohort_quiz_submissions_quiz_id", "cohort_quiz_submissions", ["quiz_id"], unique=False)
        op.create_index("ix_cohort_quiz_submissions_learner_user_id", "cohort_quiz_submissions", ["learner_user_id"], unique=False)

    if "cohort_announcements" not in existing_tables:
        op.create_table(
            "cohort_announcements",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cohort_id", sa.Integer(), nullable=True),
            sa.Column("department_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("priority", sa.String(length=20), server_default="important", nullable=False),
            sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("tags_json", sa.Text(), server_default="[]", nullable=False),
            sa.Column("author_name", sa.String(length=150), nullable=False),
            sa.Column("author_role", sa.String(length=80), server_default="Lead Instructor", nullable=False),
            sa.Column("author_avatar", sa.String(length=10), server_default="TR", nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_cohort_announcements_cohort_id", "cohort_announcements", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_announcements_department_id", "cohort_announcements", ["department_id"], unique=False)

    if "cohort_announcement_reads" not in existing_tables:
        op.create_table(
            "cohort_announcement_reads",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("announcement_id", sa.Integer(), sa.ForeignKey("cohort_announcements.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("announcement_id", "user_id", name="uq_cohort_announcement_read"),
        )
        op.create_index("ix_cohort_announcement_reads_announcement_id", "cohort_announcement_reads", ["announcement_id"], unique=False)
        op.create_index("ix_cohort_announcement_reads_user_id", "cohort_announcement_reads", ["user_id"], unique=False)

    if "cohort_discussions" not in existing_tables:
        op.create_table(
            "cohort_discussions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cohort_id", sa.Integer(), nullable=True),
            sa.Column("department_id", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("category", sa.String(length=60), server_default="Technical Q&A", nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("author_user_id", sa.Integer(), nullable=False),
            sa.Column("author_name", sa.String(length=150), nullable=False),
            sa.Column("author_role", sa.String(length=80), nullable=False),
            sa.Column("author_avatar", sa.String(length=10), server_default="TR", nullable=False),
            sa.Column("is_resolved", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_cohort_discussions_cohort_id", "cohort_discussions", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_discussions_department_id", "cohort_discussions", ["department_id"], unique=False)

    if "cohort_discussion_replies" not in existing_tables:
        op.create_table(
            "cohort_discussion_replies",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("discussion_id", sa.Integer(), sa.ForeignKey("cohort_discussions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("author_user_id", sa.Integer(), nullable=False),
            sa.Column("author_name", sa.String(length=150), nullable=False),
            sa.Column("author_role", sa.String(length=80), nullable=False),
            sa.Column("author_avatar", sa.String(length=10), server_default="TR", nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("is_trainer_reply", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_cohort_discussion_replies_discussion_id", "cohort_discussion_replies", ["discussion_id"], unique=False)

    if "cohort_discussion_likes" not in existing_tables:
        op.create_table(
            "cohort_discussion_likes",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("discussion_id", sa.Integer(), sa.ForeignKey("cohort_discussions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("discussion_id", "user_id", name="uq_cohort_discussion_like"),
        )
        op.create_index("ix_cohort_discussion_likes_discussion_id", "cohort_discussion_likes", ["discussion_id"], unique=False)
        op.create_index("ix_cohort_discussion_likes_user_id", "cohort_discussion_likes", ["user_id"], unique=False)

    if "cohort_attendance_entries" not in existing_tables:
        op.create_table(
            "cohort_attendance_entries",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("cohort_id", sa.Integer(), nullable=True),
            sa.Column("learner_user_id", sa.Integer(), nullable=False),
            sa.Column("attendance_date", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=4), server_default="P", nullable=False),
            sa.Column("session_title", sa.String(length=255), nullable=True),
            sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
            sa.Column("recorded_by_name", sa.String(length=150), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("cohort_id", "learner_user_id", "attendance_date", name="uq_cohort_attendance_day"),
        )
        op.create_index("ix_cohort_attendance_entries_cohort_id", "cohort_attendance_entries", ["cohort_id"], unique=False)
        op.create_index("ix_cohort_attendance_entries_learner_user_id", "cohort_attendance_entries", ["learner_user_id"], unique=False)
        op.create_index("ix_cohort_attendance_entries_attendance_date", "cohort_attendance_entries", ["attendance_date"], unique=False)

    if "cohort_material_bookmarks" not in existing_tables:
        op.create_table(
            "cohort_material_bookmarks",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("material_key", sa.String(length=120), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("user_id", "material_key", name="uq_cohort_material_bookmark"),
        )
        op.create_index("ix_cohort_material_bookmarks_user_id", "cohort_material_bookmarks", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for tbl in (
        "cohort_material_bookmarks",
        "cohort_attendance_entries",
        "cohort_discussion_likes",
        "cohort_discussion_replies",
        "cohort_discussions",
        "cohort_announcement_reads",
        "cohort_announcements",
        "cohort_quiz_submissions",
        "cohort_quizzes",
        "cohort_assignment_submissions",
        "cohort_assignments",
        "cohort_lessons",
        "cohort_chapters",
    ):
        if tbl in existing_tables:
            op.drop_table(tbl)
