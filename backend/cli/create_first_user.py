from __future__ import annotations

import argparse
from uuid import uuid4

from backend.cli.user_provisioning import (
    add_password_arguments,
    normalize_display_name,
    normalize_username,
    require_v2_application_database,
    resolve_password,
)
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
    add_password_arguments(parser)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    require_v2_application_database(settings)
    username = normalize_username(args.username)
    display_name = normalize_display_name(args.display_name)
    password_hash = hash_password(resolve_password(args))
    session = build_session_factory(settings)()
    try:
        repository = SqlAlchemyUserRepository(session)
        if repository.user_count() != 0:
            raise SystemExit("The first-user command refuses to run after a user already exists.")
        user = repository.create(
            username=username,
            display_name=display_name,
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
