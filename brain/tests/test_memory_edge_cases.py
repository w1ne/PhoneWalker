"""Memory edge cases — unicode, None tags, empty search, wildcards."""

from __future__ import annotations

import pytest

from brain.memory import Memory


@pytest.fixture
def mem():
    m = Memory(":memory:")
    yield m
    m.close()


def test_unicode_keys_and_values(mem):
    mem.remember("ім'я", "Андрій")
    assert mem.recall("ім'я") == "Андрій"


def test_log_episode_with_none_tags(mem):
    eid = mem.log_episode("did something", None)
    eps = mem.recent_episodes(1)
    assert eps[0].tags == []
    assert eps[0].id == eid


def test_search_no_matches_returns_empty(mem):
    mem.log_episode("bowed to the crowd")
    assert mem.search_episodes("xyzzy") == []


def test_search_with_sql_wildcards_escaped(mem):
    mem.log_episode("100% sure it worked")
    mem.log_episode("totally sure it worked")
    hits = mem.search_episodes("100%")
    assert len(hits) == 1
    assert "100%" in hits[0].summary


def test_recent_episodes_zero(mem):
    mem.log_episode("a")
    assert mem.recent_episodes(0) == []


def test_recent_episodes_more_than_exist(mem):
    mem.log_episode("only one")
    eps = mem.recent_episodes(100)
    assert len(eps) == 1
