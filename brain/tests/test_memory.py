"""SQLite memory — unit tests, no filesystem footprint."""

from __future__ import annotations

import pytest

from brain.memory import Memory


@pytest.fixture
def mem():
    m = Memory(":memory:")
    yield m
    m.close()


def test_remember_and_recall(mem):
    mem.remember("user_name", "Andrii")
    assert mem.recall("user_name") == "Andrii"


def test_recall_missing_returns_none(mem):
    assert mem.recall("nothing") is None


def test_remember_overwrites(mem):
    mem.remember("k", 1)
    mem.remember("k", 2)
    assert mem.recall("k") == 2


def test_remember_accepts_json_values(mem):
    mem.remember("config", {"stride": 150, "loud": True})
    assert mem.recall("config") == {"stride": 150, "loud": True}


def test_forget(mem):
    mem.remember("k", 1)
    assert mem.forget("k") is True
    assert mem.recall("k") is None
    assert mem.forget("k") is False


def test_all_facts(mem):
    mem.remember("a", 1)
    mem.remember("b", 2)
    assert mem.all_facts() == {"a": 1, "b": 2}


def test_episode_log_and_recent(mem):
    mem.log_episode("greeted Andrii", ["greeting"])
    mem.log_episode("jumped twice", ["play"])
    eps = mem.recent_episodes(5)
    assert len(eps) == 2
    assert eps[0].summary == "jumped twice"
    assert "play" in eps[0].tags


def test_episode_search(mem):
    mem.log_episode("bowed to the crowd")
    mem.log_episode("walked forward")
    mem.log_episode("bowed again at the end")
    hits = mem.search_episodes("bowed")
    assert len(hits) == 2
