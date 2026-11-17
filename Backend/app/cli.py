import argparse
import getpass
import sys

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import clock
from app.core.phone import normalise_phone
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import RefreshToken, User
from app.models.enums import UserRole

MIN_PASSWORD_LENGTH = 8


class CliError(Exception):
    pass


def ask_password() -> str:
    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise CliError(f"The password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if getpass.getpass("Password again: ") != password:
        raise CliError("The two passwords are not the same.")
    return password


def find_user(session: Session, login: str) -> User:
    if "@" in login:
        user = session.scalar(select(User).where(User.email == login.strip().lower()))
    else:
        phone = normalise_phone(login)
        user = session.scalar(select(User).where(User.phone == phone)) if phone else None
    if user is None:
        raise CliError(f"No user with email or phone {login}.")
    return user


def create_user(session: Session, name: str, email: str, phone: str | None, role: str) -> User:
    email = email.strip().lower()
    stored_phone = None
    if phone:
        stored_phone = normalise_phone(phone)
        if stored_phone is None:
            raise CliError(f"{phone} is not a Ghana phone number (e.g. 0241234567).")
    if session.scalar(select(User).where(User.email == email)):
        raise CliError(f"A user with email {email} already exists.")
    if stored_phone and session.scalar(select(User).where(User.phone == stored_phone)):
        raise CliError(f"A user with phone {stored_phone} already exists.")
    user = User(
        name=name,
        email=email,
        phone=stored_phone,
        role=UserRole(role),
        password_hash=hash_password(ask_password()),
    )
    session.add(user)
    return user


def set_password(session: Session, login: str) -> User:
    user = find_user(session, login)
    user.password_hash = hash_password(ask_password())
    revoke_refresh_tokens(session, user)
    return user


def set_active(session: Session, login: str, active: bool) -> User:
    user = find_user(session, login)
    user.is_active = active
    if not active:
        revoke_refresh_tokens(session, user)
    return user


def unlock(session: Session, login: str) -> User:
    user = find_user(session, login)
    user.failed_login_count = 0
    user.first_failed_login_at = None
    user.locked_until = None
    return user


def revoke_refresh_tokens(session: Session, user: User) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=clock.now())
    )


def list_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.role, User.email)))


def print_users(users: list[User]) -> None:
    print(f"{'EMAIL':32} {'PHONE':14} {'ROLE':11} {'ACTIVE':7} LOCKED UNTIL")
    for user in users:
        locked = user.locked_until.strftime("%Y-%m-%d %H:%M UTC") if user.locked_until else ""
        active = "yes" if user.is_active else "no"
        print(f"{user.email:32} {user.phone or '':14} {user.role:11} {active:7} {locked}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Manage SmartBin users")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-user", help="Add a user (asks for the password)")
    create.add_argument("--name", required=True)
    create.add_argument("--email", required=True)
    create.add_argument("--phone", help="Ghana number, e.g. 0241234567")
    create.add_argument("--role", required=True, choices=[role.value for role in UserRole])

    for name, text in [
        ("set-password", "Change a user's password (logs them out everywhere)"),
        ("deactivate", "Stop a user from logging in (logs them out everywhere)"),
        ("activate", "Let a deactivated user log in again"),
        ("unlock", "Clear a lockout after too many failed logins"),
    ]:
        command = commands.add_parser(name, help=text)
        command.add_argument("login", help="Email or phone")

    commands.add_parser("list-users", help="Show all users")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with SessionLocal() as session:
            if args.command == "list-users":
                print_users(list_users(session))
                return 0
            if args.command == "create-user":
                user = create_user(session, args.name, args.email, args.phone, args.role)
                done = "Created"
            elif args.command == "set-password":
                user = set_password(session, args.login)
                done = "Password changed for"
            elif args.command == "deactivate":
                user = set_active(session, args.login, False)
                done = "Deactivated"
            elif args.command == "activate":
                user = set_active(session, args.login, True)
                done = "Activated"
            else:
                user = unlock(session, args.login)
                done = "Unlocked"
            session.commit()
            print(f"{done} {user.role} {user.email}")
    except (CliError, KeyboardInterrupt) as error:
        print(f"Error: {error}" if str(error) else "Cancelled.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
