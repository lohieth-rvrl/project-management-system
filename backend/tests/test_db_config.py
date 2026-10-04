import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.management import call_command

BACKEND = Path(__file__).resolve().parent.parent
BASE_ENV = {
    "PATH": os.environ.get("PATH", ""),
    "DJANGO_SECRET_KEY": "x" * 50,
    "DJANGO_DEBUG": "0",
}


def load_settings(**env):
    """Import config.settings in a clean process and return (exit_code, output)."""
    code = (
        "import json, config.settings as s;"
        "print(json.dumps({'db': {k: str(v) for k, v in s.DATABASES['default'].items()}}))"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True,
                       text=True, env={**BASE_ENV, **env})
    return r.returncode, r.stdout.strip(), r.stderr


def test_schema_sets_search_path():
    rc, out, err = load_settings(DATABASE_URL="postgres://u:p@host:5432/dbname", DB_SCHEMA="pms")
    assert rc == 0, err
    db = json.loads(out)["db"]
    assert "search_path=pms" in db["OPTIONS"]
    assert db["NAME"] == "dbname"


def test_no_schema_means_no_search_path_option():
    rc, out, err = load_settings(DATABASE_URL="postgres://u:p@host:5432/dbname")
    assert rc == 0, err
    assert "search_path" not in json.loads(out)["db"].get("OPTIONS", "")


@pytest.mark.parametrize("bad", ["pms; drop table x", "a-b", "1abc", "pms space", "x" * 70])
def test_bad_schema_names_are_rejected(bad):
    rc, _, err = load_settings(DATABASE_URL="postgres://u:p@host:5432/dbname", DB_SCHEMA=bad)
    assert rc != 0 and "DB_SCHEMA" in err


def test_production_without_database_refuses_to_start():
    rc, _, err = load_settings()
    assert rc != 0 and "DATABASE_URL" in err


def test_production_without_secret_key_refuses_to_start():
    env = {"DATABASE_URL": "postgres://u:p@host:5432/dbname", "DJANGO_SECRET_KEY": ""}
    rc, _, err = load_settings(**env)
    assert rc != 0 and "DJANGO_SECRET_KEY" in err


@pytest.mark.django_db
def test_ensure_schema_is_a_noop_on_sqlite(monkeypatch, capsys):
    monkeypatch.setenv("DB_SCHEMA", "pms")
    call_command("ensure_schema")  # test database is SQLite: must not raise
    assert "nothing to do" in capsys.readouterr().out
