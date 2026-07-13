"""HTTP endpoint tests (Flask test client; LLM stubbed in conftest)."""
from __future__ import annotations

import pytest
from app import app as flask_app


@pytest.fixture
def client(patch_data_dir):
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_run_requires_task(client):
    r = client.post("/run")
    assert r.status_code == 400


def test_run_executes(client, data_dir):
    r = client.post("/run", query_string={"task": "count Wednesdays in dates.txt"})
    assert r.status_code == 200
    assert "found" in r.get_json()["result"]


def test_run_specific_plan(client, monkeypatch, data_dir):
    from agent import llm

    monkeypatch.setattr(
        llm,
        "chat",
        lambda messages, **kw: '{"operations": [{"operation": "sort_contacts"}]}',
    )
    r = client.post("/run", query_string={"task": "sort contacts"})
    assert r.status_code == 200
    assert (data_dir / "contacts-sorted.json").exists()


def test_read_ok(client, data_dir):
    (data_dir / "hello.txt").write_text("hi", encoding="utf-8")
    r = client.get("/read", query_string={"path": "hello.txt"})
    assert r.status_code == 200
    assert r.get_data(as_text=True) == "hi"


def test_read_missing(client):
    r = client.get("/read", query_string={"path": "nope.txt"})
    assert r.status_code == 404


def test_read_traversal_blocked(client):
    r = client.get("/read", query_string={"path": "../../etc/passwd"})
    assert r.status_code == 403


def test_filter_csv(client, data_dir):
    csv_path = data_dir / "people.csv"
    csv_path.write_text("name,role\nAlice,admin\nBob,user\n", encoding="utf-8")
    r = client.get(
        "/filter_csv",
        query_string={"path": "people.csv", "column": "role", "value": "admin"},
    )
    assert r.status_code == 200
    rows = r.get_json()
    assert len(rows) == 1 and rows[0]["name"] == "Alice"
