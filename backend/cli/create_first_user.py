from __future__ import annotations

import argparse
import getpass
from uuid import uuid4

from backend.config import Settings
from backend.db import build_session_factory
from backend.domain.roles import UserRole
from backend.repositories.users import SqlAlchemyUserRepository
from backend.services.audit import append_audit_event
from backend.services.passwords import hash_password


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first QuoteOps AI V2 admin user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--password", help="Omit to enter the password without echoing it.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    if not settings.database_is_configured:
        raise SystemExit("A V2-only PostgreSQL database must be configured before creating a user.")
    if settings.auth_secret is None or settings.auth_secret.get_secret_value().startswith("CHANGE_ME"):
        raise SystemExit("A configured V2 authentication secret is required before creating a user.")

    password = args.password or getpass.getpass("Password: ")
    password_hash = hash_password(password)
    session = build_session_factory(settings)()
    try:
        repository = SqlAlchemyUserRepository(session)
        if repository.user_count() != 0:
            raise SystemExit("The first-user command refuses to run after a user already exists.")
        user = repository.create(
            username=args.username,
            display_name=args.display_name,
            password_hash=password_hash,
            role=UserRole.ADMIN,
        )
        append_audit_event(
            session,
            actor_user_id=user.id,
            action="user.first_admin_created",
            entity_type="user",
            entity_id=str(user.id),
            request_id=f"cli-{uuid4()}",
            metadata={"role": UserRole.ADMIN.value},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print("First V2 admin user created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
