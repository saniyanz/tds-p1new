"""Operation handler tests (no network; LLM stubbed in conftest)."""
from __future__ import annotations

import json
import shutil
import sqlite3

import pytest
from dateutil.parser import parse
from operations import (
    audio,
    comments,
    contacts,
    credit_card,
    dates,
    docs,
    email,
    fetch_api,
    format_file,
    image,
    logs,
    markdown,
    scrape,
    sql_query,
    tickets,
)


def _wednesday_count(data_dir):
    cnt = 0
    for line in (data_dir / "dates.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            if parse(line, fuzzy=True).weekday() == 2:
                cnt += 1
        except Exception:
            pass
    return cnt


def test_count_dates(patch_data_dir, data_dir):
    expected = _wednesday_count(data_dir)
    out = dates.handle_count_dates("Wednesday")
    assert f"found {expected} Wednesdays" in out
    assert (data_dir / "dates-wednesday.txt").read_text().strip() == str(expected)


def test_count_dates_invalid(patch_data_dir):
    with pytest.raises(ValueError):
        dates.handle_count_dates("Notaday")


def test_sort_contacts(patch_data_dir, data_dir):
    contacts.handle_sort_contacts()
    sorted_contacts = json.loads((data_dir / "contacts-sorted.json").read_text())
    keys = [(c["last_name"], c["first_name"]) for c in sorted_contacts]
    assert keys == sorted(keys)


def test_extract_logs(patch_data_dir, data_dir):
    logs.handle_extract_logs()
    lines = (data_dir / "logs-recent.txt").read_text().splitlines()
    assert len(lines) == 10


def test_index_docs(patch_data_dir, data_dir):
    docs.handle_index_docs()
    index = json.loads((data_dir / "docs" / "index.json").read_text())
    md_files = list(data_dir.glob("docs/**/*.md"))
    assert len(index) == len(md_files)
    for rel in index.values():
        assert isinstance(rel, str) and rel


def test_extract_email(patch_data_dir, data_dir):
    email.handle_extract_email()
    sender = (data_dir / "email-sender.txt").read_text().strip()
    assert "@" in sender


def test_find_similar_comments(patch_data_dir, data_dir):
    comments.handle_find_similar_comments()
    out = (data_dir / "comments-similar.txt").read_text().splitlines()
    assert len(out) == 2
    assert all(line.strip() for line in out)


def test_query_tickets(patch_data_dir, data_dir):
    tickets.handle_query_tickets("Gold")
    expected = _gold_total(data_dir)
    assert (data_dir / "ticket-sales-gold.txt").read_text().strip() == str(expected)


def _gold_total(data_dir):
    with sqlite3.connect(data_dir / "ticket-sales.db") as conn:
        return conn.execute(
            "SELECT SUM(units*price) FROM tickets WHERE type='Gold'"
        ).fetchone()[0]


def test_md_to_html(patch_data_dir, data_dir):
    (data_dir / "sample.md").write_text("# Hello\n\nsome *text*", encoding="utf-8")
    markdown.handle_md_to_html("sample.md", "sample.html")
    html = (data_dir / "sample.html").read_text()
    assert "<h1" in html and "Hello" in html


def test_resize_image(patch_data_dir, data_dir):
    from PIL import Image

    src = data_dir / "in.jpg"
    Image.new("RGB", (400, 400), (120, 80, 200)).save(src, format="JPEG")
    image.handle_resize_image("in.jpg", "out.jpg", max_width=100, max_height=100)
    with Image.open(data_dir / "out.jpg") as im:
        assert max(im.size) <= 100


def test_run_sql_query(patch_data_dir, data_dir):
    sql_query.handle_run_sql_query(
        "ticket-sales.db", "SELECT COUNT(*) FROM tickets"
    )
    res = (data_dir / "sql_query_result.txt").read_text()
    assert "1000" in res


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract binary missing")
def test_extract_credit_card(patch_data_dir, data_dir):
    credit_card.handle_extract_credit_card()
    num = (data_dir / "credit_card.txt").read_text().strip()
    assert num.isdigit()


def test_format_file_mocked(patch_data_dir, data_dir, monkeypatch):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        import subprocess

        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("operations.format_file.subprocess.run", fake_run)
    out = format_file.handle_format_file()
    assert "format_file" in out
    assert "prettier" in calls["cmd"][1]


def test_fetch_api_mocked(patch_data_dir, data_dir, monkeypatch):
    class Resp:
        text = '{"ok": true}'

        def raise_for_status(self):
            pass

    monkeypatch.setattr(fetch_api.requests, "get", lambda *a, **k: Resp())
    fetch_api.handle_fetch_api("https://x.test/a", "a.json")
    assert json.loads((data_dir / "a.json").read_text())["ok"]


def test_scrape_mocked(patch_data_dir, data_dir, monkeypatch):
    class Resp:
        text = "<html><body><h1>Title</h1></body></html>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(scrape.requests, "get", lambda *a, **k: Resp())
    scrape.handle_scrape_website("https://x.test", "page.txt")
    assert "Title" in (data_dir / "page.txt").read_text()


def test_transcribe_audio_mocked(patch_data_dir, data_dir, monkeypatch):
    # Force the fallback path (no real STT credentials).
    monkeypatch.setattr(audio, "_transcribe", lambda p: "hello world")
    (data_dir / "clip.mp3").write_text("dummy", encoding="utf-8")
    audio.handle_transcribe_audio("clip.mp3", "clip.txt")
    assert (data_dir / "clip.txt").read_text() == "hello world"
