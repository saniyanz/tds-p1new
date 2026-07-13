"""Shared pytest fixtures.

Generates deterministic /data fixtures with ``datagen`` into a temp directory
and points the app's settings at it, so tests never touch the real /data and
never need the network.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("AIPROXY_TOKEN", "test-token")
os.environ.setdefault("ENABLE_LLM_CACHE", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import datagen  # noqa: E402
from core import config  # noqa: E402


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("data")
    datagen.config["email"] = "23f2002592@ds.study.iitm.ac.in"
    datagen.config["root"] = str(root)
    datagen.a2_format_markdown()
    datagen.a3_dates()
    datagen.a4_contacts()
    datagen.a5_logs()
    datagen.a6_docs()
    datagen.a7_email()
    datagen.a8_credit_card_image()
    datagen.a9_comments()
    datagen.a10_ticket_sales()
    return root


@pytest.fixture
def patch_data_dir(data_dir, monkeypatch):
    monkeypatch.setattr(config.settings, "data_dir", Path(data_dir))
    yield


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Stub out the LLM so tests never hit the network."""
    import numpy as np
    from agent import llm

    def fake_chat(messages, **kwargs):
        # Minimal canned plan: count Wednesdays. Tests that need other plans
        # monkeypatch this themselves.
        return '{"operations": [{"operation": "count_dates", "day_name": "Wednesday"}]}'

    def fake_embedding(text: str):
        # Deterministic pseudo-embedding so cosine math is stable.
        rng = np.random.RandomState(abs(hash(text)) % (2**32))
        vec = rng.rand(8).astype("float32")
        return list(vec / np.linalg.norm(vec))

    monkeypatch.setattr(llm, "chat", fake_chat)
    monkeypatch.setattr(llm, "get_embedding", fake_embedding)
    yield
