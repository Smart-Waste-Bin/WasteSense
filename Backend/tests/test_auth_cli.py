import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import cli
from app.core.phone import normalise_phone
from app.core.security import verify_password
from app.models import User


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0241234567", "+233241234567"),
        ("024 123 4567", "+233241234567"),
        ("024-123-4567", "+233241234567"),
        ("233241234567", "+233241234567"),
        ("+233241234567", "+233241234567"),
        ("241234567", None),
        ("02412345678", None),
        ("+44241234567", None),
        ("phone", None),
    ],
)
def test_normalise_phone(value, expected):
    assert normalise_phone(value) == expected


@pytest.fixture
def cli_db(migrated_engine, monkeypatch):
    make_session = sessionmaker(migrated_engine)
    monkeypatch.setattr(cli, "SessionLocal", make_session)
    return make_session


def typed_passwords(monkeypatch, *answers):
    replies = iter(answers)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: next(replies))


def create(name="Ama Mensah", email="Ama@Example.com", phone="0241234567", role="supervisor"):
    args = ["create-user", "--name", name, "--email", email, "--role", role]
    return cli.main(args + (["--phone", phone] if phone else []))


def test_create_user(cli_db, monkeypatch, capsys):
    typed_passwords(monkeypatch, "good-password", "good-password")
    assert create() == 0
    with cli_db() as session:
        user = session.scalar(select(User))
        assert user is not None
        assert user.email == "ama@example.com"
        assert user.phone == "+233241234567"
        assert user.role == "supervisor"
        assert user.password_hash != "good-password"
        assert verify_password("good-password", user.password_hash)
    assert "good-password" not in capsys.readouterr().out


@pytest.mark.parametrize(
    ("answers", "message"),
    [(["short", "short"], "at least 8"), (["good-password", "other-password"], "not the same")],
)
def test_create_user_rejects_bad_passwords(cli_db, monkeypatch, capsys, answers, message):
    typed_passwords(monkeypatch, *answers)
    assert create() == 1
    assert message in capsys.readouterr().err
    with cli_db() as session:
        assert session.scalar(select(User)) is None


def test_create_user_rejects_duplicates_and_bad_phones(cli_db, monkeypatch, capsys):
    typed_passwords(monkeypatch, *["good-password"] * 6)
    assert create() == 0
    assert create(name="Copy") == 1
    assert create(email="other@example.com") == 1  # same phone
    assert create(email="third@example.com", phone="12345") == 1
    assert "not a Ghana phone number" in capsys.readouterr().err


def test_deactivate_activate_unlock_and_set_password(cli_db, monkeypatch):
    typed_passwords(monkeypatch, "good-password", "good-password", "new-password", "new-password")
    create()
    with cli_db() as session:
        user = session.scalar(select(User))
        assert user is not None
        user.failed_login_count = 3
        session.commit()

    assert cli.main(["deactivate", "ama@example.com"]) == 0
    assert cli.main(["activate", "0241234567"]) == 0
    assert cli.main(["unlock", "+233241234567"]) == 0
    assert cli.main(["set-password", "AMA@example.com"]) == 0
    with cli_db() as session:
        user = session.scalar(select(User))
        assert user is not None
        assert user.is_active is True
        assert user.failed_login_count == 0
        assert verify_password("new-password", user.password_hash)


def test_unknown_user(cli_db, capsys):
    assert cli.main(["deactivate", "nobody@example.com"]) == 1
    assert "No user" in capsys.readouterr().err


def test_list_users(cli_db, monkeypatch, capsys):
    typed_passwords(monkeypatch, "good-password", "good-password")
    create()
    assert cli.main(["list-users"]) == 0
    out = capsys.readouterr().out
    assert "ama@example.com" in out and "+233241234567" in out and "supervisor" in out
