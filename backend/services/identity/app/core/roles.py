
from enum import StrEnum


class Role(StrEnum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    TEACHER = "teacher"
    LEARNER = "learner"


class Permission(StrEnum):
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    MANAGE_DEPARTMENTS = "manage_departments"
    MANAGE_COURSES = "manage_courses"
    MANAGE_COHORTS = "manage_cohorts"
    MANAGE_ENROLLMENTS = "manage_enrollments"
    MANAGE_MATERIALS = "manage_materials"
    MANAGE_ATTENDANCE = "manage_attendance"
    VIEW_ASSIGNED_TRAINING = "view_assigned_training"
    VIEW_OWN_TRAINING = "view_own_training"
    MANAGE_ASSESSMENTS = "manage_assessments"
    VIEW_OWN_RESULTS = "view_own_results"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    # Full platform access
    Role.SUPERADMIN: frozenset(Permission),

    # Manage users and training operations within authorized scope
    Role.ADMIN: frozenset({
        Permission.MANAGE_USERS,
        Permission.MANAGE_DEPARTMENTS,
        Permission.MANAGE_COURSES,
        Permission.MANAGE_COHORTS,
        Permission.MANAGE_ENROLLMENTS,
        Permission.MANAGE_MATERIALS,
        Permission.MANAGE_ATTENDANCE,
        Permission.MANAGE_ASSESSMENTS,
        Permission.VIEW_ASSIGNED_TRAINING,
        Permission.VIEW_OWN_TRAINING,
        Permission.VIEW_OWN_RESULTS,
    }),

    # Teaching and assigned training operations
    Role.TEACHER: frozenset({
        Permission.MANAGE_MATERIALS,
        Permission.MANAGE_ATTENDANCE,
        Permission.MANAGE_ASSESSMENTS,
        Permission.VIEW_ASSIGNED_TRAINING,
    }),

    # Personal learning access
    Role.LEARNER: frozenset({
        Permission.VIEW_OWN_TRAINING,
        Permission.VIEW_OWN_RESULTS,
    }),
}
