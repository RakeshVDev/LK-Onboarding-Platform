
from sqlalchemy import select

from services.identity.app.db.session import SessionLocal
from services.identity.app.models.user import User
from services.identity.app.core.roles import Role


def main():
    email = input("Enter registered email: ").strip().lower()

    if input("Type PROMOTE to continue: ").strip() != "PROMOTE":
        print("Cancelled.")
        return

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == email)
        )

        if user is None:
            print("User not found.")
            return

        if not user.is_active:
            print("User is inactive. Promotion cancelled.")
            return

        user.role = Role.SUPERADMIN.value
        db.commit()

        print(f"Superadmin assigned to {user.email}")


if __name__ == "__main__":
    main()
