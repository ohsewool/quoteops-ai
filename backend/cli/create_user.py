"""Explicitly provision a subsequent local review user after the first admin."""

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
    parser = argparse.ArgumentParser(description="Create an explicit QuoteOps AI V2 review user.")
    parser.add_argument("--actor-username", required=True, help="Existing active admin operating this command.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--role", required=True, choices=[role.value for role in UserRole])
    add_password_arguments(parser)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    require_v2_application_database(settings)
    actor_username = normalize_username(args.actor_username)
    username = normalize_username(args.username)
    display_name = normalize_display_name(args.display_name)
    role = UserRole(args.role)
    password_hash = hash_password(resolve_password(args))
    session = build_session_factory(settings)()
    try:
        repository = SqlAlchemyUserRepository(session)
        if repository.user_count() == 0:
            raise SystemExit("Run create_first_user before provisioning additional review users.")
        actor = repository.get_by_username(actor_username)
        if actor is None or not actor.active or actor.role is not UserRole.ADMIN:
            raise SystemExit("An existing active admin is required to provision a review user.")
        if repository.get_by_username(username) is not None:
            raise SystemExit("A user with that username already exists.")
        user = repository.create(
            username=username,
            display_name=display_name,
            password_hash=password_hash,
            role=role,
        )
        append_audit_event(
            session,
            actor_user_id=actor.id,
            action="user.provisioned",
            entity_type="user",
            entity_id=str(user.id),
            request_id=f"cli-{uuid4()}",
            metadata={"role": role.value, "provisioned_by_cli": True},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print("V2 review user created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
