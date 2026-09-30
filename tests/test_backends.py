"""Tests for the sqlite, postgres, and mysql backends plus the CLI dispatcher."""

import importlib.metadata
import sqlite3

import psycopg
import pytest
from click.testing import CliRunner

from llm_sql_prompt import main
from llm_sql_prompt import mysql as mysql_backend
from llm_sql_prompt import postgres as postgres_backend
from llm_sql_prompt import sqlite as sqlite_backend
from llm_sql_prompt import util as util_module
from llm_sql_prompt import version as version_module


class FakeCursor:
    """A cursor that replays a scripted queue of results."""

    def __init__(self, script):
        self._script = script
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if self._script and self._script[0][0] == "raise":
            _, exc = self._script.pop(0)
            raise exc

    def fetchall(self):
        kind, payload = self._script.pop(0)
        assert kind == "fetchall"
        return payload

    def fetchone(self):
        kind, payload = self._script.pop(0)
        assert kind == "fetchone"
        return payload[0] if payload else None


class FakeConn:
    """A connection handing out FakeCursors over a shared result script."""

    def __init__(self, script, database="testdb"):
        self._script = list(script)
        self.database = database
        self.closed = False

    def cursor(self):
        return FakeCursor(self._script)

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _mysql_schema_script():
    return [
        ("fetchone", [("A users table",)]),
        ("fetchall", [("id", "int", None, ""), ("name", "varchar", 255, "User name")]),
        ("fetchall", [("team_id", "teams", "id")]),
        ("fetchall", [(1, "ann"), (2, "bob")]),
        ("fetchall", [("id",), ("name",)]),
    ]


def _postgres_schema_script():
    return [
        ("fetchall", [("uuid-ossp", "1.1", "")]),
        ("fetchone", [("16.2",)]),
        ("fetchone", [("Table comment",)]),
        ("fetchall", [("id", "integer", None)]),
        ("fetchall", []),
        ("fetchone", [("id", "PK")]),
        ("fetchall", [(1,)]),
        ("fetchall", [("id",)]),
    ]


def test_cli_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "DATABASE_URL" in result.output


def test_cli_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "llm-sql-prompt version" in result.output


def test_cli_unknown_database_type():
    result = CliRunner().invoke(main, ["/tmp/llm-sql-prompt-missing-xyz"])
    assert result.exit_code == 1
    assert "Unknown database type" in result.output


def test_cli_dispatch_postgres(monkeypatch):
    called = {}
    monkeypatch.setattr(
        postgres_backend,
        "describe_database_and_table",
        lambda *args: called.setdefault("hit", args),
    )
    result = CliRunner().invoke(main, ["postgresql://u:p@localhost/db", "users"])
    assert result.exit_code == 0
    assert called["hit"][0] == "postgresql://u:p@localhost/db"


def test_cli_dispatch_mysql(monkeypatch):
    called = {}
    monkeypatch.setattr(
        mysql_backend,
        "describe_database_and_table",
        lambda *args: called.setdefault("hit", args),
    )
    result = CliRunner().invoke(main, ["mysql://u:p@localhost/db", "users"])
    assert result.exit_code == 0
    assert called["hit"][0] == "mysql://u:p@localhost/db"


def test_cli_dispatch_sqlite(monkeypatch):
    called = {}
    monkeypatch.setattr(
        sqlite_backend,
        "describe_database_and_table",
        lambda *args: called.setdefault("hit", args),
    )
    result = CliRunner().invoke(main, ["sqlite:///tmp/fake.db", "users"])
    assert result.exit_code == 0
    assert called["hit"][0] == "sqlite:///tmp/fake.db"


def test_parse_mysql_url_defaults():
    assert mysql_backend.parse_mysql_url("mysql://localhost") == {
        "user": "root",
        "password": "",
        "host": "localhost",
        "port": 3306,
        "database": None,
    }


def test_parse_mysql_url_full():
    assert mysql_backend.parse_mysql_url("mysql://bob:secret@dbhost:3307/appdb") == {
        "user": "bob",
        "password": "secret",
        "host": "dbhost",
        "port": 3307,
        "database": "appdb",
    }


def test_check_mysql_available():
    mysql_backend.check_mysql_available()


def test_check_mysql_missing(monkeypatch):
    monkeypatch.setattr(mysql_backend, "MYSQL_AVAILABLE", False)
    with pytest.raises(ImportError, match="mysql-connector-python"):
        mysql_backend.check_mysql_available()


def test_connect_to_mysql_passes_params(monkeypatch):
    seen = {}

    def fake_connect(**kwargs):
        seen.update(kwargs)
        return FakeConn([], database=kwargs.get("database"))

    monkeypatch.setattr("mysql.connector.connect", fake_connect)
    conn = mysql_backend.connect_to_mysql("mysql://bob:secret@dbhost:3307/appdb")
    assert seen == {
        "user": "bob",
        "password": "secret",
        "host": "dbhost",
        "port": 3307,
        "database": "appdb",
    }
    assert conn.database == "appdb"


def test_mysql_describe_table_schema(capsys):
    conn = FakeConn(
        [
            ("fetchall", [("id", "int", None, "")]),
            ("fetchall", []),
        ]
    )
    mysql_backend.describe_table_schema(conn, "users")
    out = capsys.readouterr().out
    assert "id int" in out


def test_mysql_get_table_names(monkeypatch):
    fake = FakeConn([("fetchall", [("users",), ("teams",)])])
    monkeypatch.setattr(mysql_backend, "connect_to_mysql", lambda url: fake)
    assert mysql_backend.get_table_names("mysql://u@localhost/db") == ["users", "teams"]
    assert fake.closed


def test_mysql_describe_full(capsys, monkeypatch):
    conn = FakeConn(_mysql_schema_script())
    monkeypatch.setattr(mysql_backend, "connect_to_mysql", lambda url: conn)
    mysql_backend.describe_database_and_table(
        "mysql://u@localhost/db", ("users",), False
    )
    out = capsys.readouterr().out
    assert "MySQL database" in out
    assert "A users table" in out
    assert "name varchar(255) -- User name" in out
    assert "INSERT INTO users" in out


def test_mysql_describe_no_data(capsys, monkeypatch):
    conn = FakeConn(_mysql_schema_script())
    monkeypatch.setattr(mysql_backend, "connect_to_mysql", lambda url: conn)
    mysql_backend.describe_database_and_table(
        "mysql://u@localhost/db", ("users",), False, include_data=False
    )
    out = capsys.readouterr().out
    assert "INSERT INTO users" not in out


def test_mysql_describe_all_tables(monkeypatch, capsys):
    conn = FakeConn(_mysql_schema_script())
    monkeypatch.setattr(mysql_backend, "get_table_names", lambda url: ["users"])
    monkeypatch.setattr(mysql_backend, "connect_to_mysql", lambda url: conn)
    mysql_backend.describe_database_and_table("mysql://u@localhost/db", (), True)
    assert "INSERT INTO users" in capsys.readouterr().out


def test_mysql_no_tables_exits(monkeypatch):
    monkeypatch.setattr(mysql_backend, "get_table_names", lambda url: ["users"])
    with pytest.raises(SystemExit):
        mysql_backend.describe_database_and_table("mysql://u@localhost/db", (), False)


def test_postgres_get_table_names(monkeypatch):
    monkeypatch.setattr(
        "llm_sql_prompt.postgres.psycopg.connect",
        lambda *args, **kwargs: FakeConn([("fetchall", [("a",), ("b",)])]),
    )
    assert postgres_backend.get_table_names("postgresql://u@localhost/db") == ["a", "b"]


def test_postgres_describe_full(capsys, monkeypatch):
    monkeypatch.setattr(
        "llm_sql_prompt.postgres.psycopg.connect",
        lambda *args, **kwargs: FakeConn(_postgres_schema_script()),
    )
    postgres_backend.describe_database_and_table(
        "postgresql://u@localhost/db", ("users",), False
    )
    out = capsys.readouterr().out
    assert "PostgreSQL database (server version: 16.2)" in out
    assert "uuid-ossp" in out
    assert "Table comment" in out
    assert "INSERT INTO users" in out


def test_postgres_server_version_fallback(capsys, monkeypatch):
    script = _postgres_schema_script()
    script[1] = ("raise", psycopg.Error("SHOW failed"))
    script.insert(2, ("fetchone", [("PostgreSQL 16.2 on x86_64",)]))
    monkeypatch.setattr(
        "llm_sql_prompt.postgres.psycopg.connect",
        lambda *args, **kwargs: FakeConn(script),
    )
    postgres_backend.describe_database_and_table(
        "postgresql://u@localhost/db", ("users",), False
    )
    assert "server version: 16.2" in capsys.readouterr().out


def test_postgres_server_version_unknown(capsys, monkeypatch):
    script = [
        ("fetchall", []),
        ("raise", psycopg.Error("SHOW failed")),
        ("raise", psycopg.Error("SELECT failed")),
        ("fetchone", [[None]]),
        ("fetchall", [("id", "integer", None)]),
        ("fetchall", []),
        ("fetchone", []),
        ("fetchall", []),
        ("fetchall", [("id",)]),
    ]
    monkeypatch.setattr(
        "llm_sql_prompt.postgres.psycopg.connect",
        lambda *args, **kwargs: FakeConn(script),
    )
    postgres_backend.describe_database_and_table(
        "postgresql://u@localhost/db", ("users",), False, include_data=False
    )
    out = capsys.readouterr().out
    assert "server version: unknown" in out
    assert "No PostgreSQL extensions installed" in out


def test_postgres_no_tables_exits(monkeypatch):
    monkeypatch.setattr(postgres_backend, "get_table_names", lambda url: ["users"])
    with pytest.raises(SystemExit):
        postgres_backend.describe_database_and_table(
            "postgresql://u@localhost/db", (), False
        )


def _make_sqlite_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO users (name) VALUES ('ann'), ('bob')")
    conn.commit()
    conn.close()


def test_sqlite_list_tables(tmp_path):
    db = str(tmp_path / "t.db")
    _make_sqlite_db(db)
    assert "users" in sqlite_backend.list_sqllite_tables(db)


def test_sqlite_describe_with_data(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    _make_sqlite_db(db)
    sqlite_backend.describe_database_and_table(db, ("users",), False)
    out = capsys.readouterr().out
    assert "CREATE TABLE users" in out
    assert "INSERT INTO users" in out


def test_sqlite_describe_no_data(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    _make_sqlite_db(db)
    sqlite_backend.describe_database_and_table(
        db, ("users",), False, include_data=False
    )
    out = capsys.readouterr().out
    assert "CREATE TABLE users" in out
    assert "INSERT INTO" not in out


def test_sqlite_no_tables_exits(tmp_path):
    db = str(tmp_path / "t.db")
    _make_sqlite_db(db)
    with pytest.raises(SystemExit):
        sqlite_backend.describe_database_and_table(db, (), False)


def test_get_version_installed():
    assert isinstance(version_module.get_version(), str)


def test_get_version_dev_suffix(monkeypatch):
    monkeypatch.setattr(version_module, "is_local_source_checkout", lambda: True)
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.8.0")
    assert version_module.get_version() == "0.8.0.dev"


def test_get_version_fallback(monkeypatch):
    def raise_not_found(name):
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(version_module, "is_local_source_checkout", lambda: True)
    monkeypatch.setattr(importlib.metadata, "version", raise_not_found)
    assert version_module.get_version() == "0.1.0.dev"


def test_get_version_not_a_checkout(monkeypatch):
    monkeypatch.setattr(version_module, "is_local_source_checkout", lambda: False)
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.8.0")
    assert version_module.get_version() == "0.8.0"


def test_system_prompt():
    assert "SQL" in util_module.system_prompt()
