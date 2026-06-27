"""Iteration 5 tests: the sweep harness — offline, no AWS, no cost.

A fake agent simulates the only behaviour the harness cares about: a fact seeded under
an actor (memory ON) is recalled by a later, different-session agent for the SAME actor;
with memory OFF nothing is recalled (the baseline floor). That lets us prove the harness
machinery — variant-config construction, baseline inclusion, repeat averaging, and the
table/CSV output — without touching Bedrock.
"""

from __future__ import annotations

import csv

import pytest

from agent.config import MemoryConfig
from harness.sweep import build_variant_config, format_table, run_sweep, write_csv
from probes import Probe

# A tiny fixed probe set for deterministic tests (the real one lives in probes/).
_PROBES = (
    Probe(seed="My favorite fruit is mango.", question="fav fruit?", expected=("mango",)),
    Probe(seed="I live in Lisbon.", question="city?", expected=("lisbon",)),
)


class _FakeWorld:
    """Simulates cross-session long-term memory keyed by actor id."""

    def __init__(self) -> None:
        self.ltm: dict[str, list[str]] = {}


class _FakeAgent:
    """Stores each turn under its actor when memory is on, and recalls all of them.

    Memory OFF -> stores nothing, recalls nothing (the baseline). Memory ON -> a fact
    seeded by one agent is visible to any later agent with the same actor_id, exactly
    like AgentCore long-term memory crossing a session boundary.
    """

    def __init__(self, world: _FakeWorld, mem_cfg: MemoryConfig) -> None:
        self._world = world
        self._cfg = mem_cfg
        # Mirror build_agent: a session-manager object when memory is on, else None.
        self.memory_session_manager = object() if mem_cfg.enabled else None

    def __call__(self, prompt: str) -> str:
        if not self._cfg.enabled:
            return "I don't have that information."
        self._world.ltm.setdefault(self._cfg.actor_id, []).append(prompt)
        return "From memory: " + " ".join(self._world.ltm[self._cfg.actor_id])


def _builder(world: _FakeWorld):
    return lambda mem_cfg: _FakeAgent(world, mem_cfg)


def _base_cfg(**kw) -> MemoryConfig:
    return MemoryConfig(memory_id="m-1", namespace="semantic/{actorId}", actor_id="a", session_id="s", **kw)


# --- build_variant_config: exactly one parameter varies (ADR-003) -------------

def test_variant_changes_only_the_swept_param():
    base = _base_cfg(top_k=10, relevance_score=0.2, batch_size=1)
    variant = build_variant_config(base, "top_k", "3")
    assert variant.top_k == 3 and isinstance(variant.top_k, int)
    assert variant.relevance_score == base.relevance_score
    assert variant.batch_size == base.batch_size
    assert variant.actor_id == base.actor_id
    assert variant.enabled is True


def test_variant_rejects_unknown_param():
    with pytest.raises(ValueError):
        build_variant_config(_base_cfg(), "namespace", "x")


def test_variant_coerces_and_validates_range():
    # top_k=0 is out of range -> MemoryConfig.__post_init__ rejects it.
    with pytest.raises(ValueError):
        build_variant_config(_base_cfg(), "top_k", "0")


# --- run_sweep: baseline included, memory beats the floor ---------------------

def test_sweep_includes_baseline_first_and_one_row_per_value():
    rows = run_sweep("top_k", ["1", "5"], _base_cfg(), _builder(_FakeWorld()), probes=_PROBES)
    assert len(rows) == 3  # baseline + 2 values
    assert "baseline" in rows[0].label.lower()
    assert rows[1].label == "top_k=1"
    assert rows[2].label == "top_k=5"


def test_sweep_baseline_is_floor_and_memory_recalls():
    rows = run_sweep("top_k", ["3"], _base_cfg(), _builder(_FakeWorld()), probes=_PROBES)
    baseline, mem = rows[0], rows[1]
    assert baseline.recall == 0.0   # no memory -> cannot recall across sessions
    assert mem.recall == 1.0        # memory -> recalls the seeded fact
    assert mem.recall > baseline.recall


def test_sweep_repeats_are_averaged():
    rows = run_sweep("top_k", ["3"], _base_cfg(), _builder(_FakeWorld()), probes=_PROBES, repeats=3)
    assert all(r.repeats == 3 for r in rows)
    assert rows[1].recall == 1.0  # deterministic fake -> averaging 1.0 thrice is 1.0


def test_sweep_rejects_bad_repeats():
    with pytest.raises(ValueError):
        run_sweep("top_k", ["3"], _base_cfg(), _builder(_FakeWorld()), probes=_PROBES, repeats=0)


def test_sweep_rejects_unknown_param():
    with pytest.raises(ValueError):
        run_sweep("strategy", ["semantic"], _base_cfg(), _builder(_FakeWorld()), probes=_PROBES)


# --- output: table + CSV ------------------------------------------------------

def test_format_table_has_header_and_all_rows():
    rows = run_sweep("top_k", ["1", "5"], _base_cfg(), _builder(_FakeWorld()), probes=_PROBES)
    table = format_table(rows)
    assert "config" in table and "recall" in table
    assert "baseline" in table.lower() and "top_k=1" in table and "top_k=5" in table


def test_write_csv_roundtrip(tmp_path):
    rows = run_sweep("top_k", ["1"], _base_cfg(), _builder(_FakeWorld()), probes=_PROBES)
    out = tmp_path / "r.csv"
    write_csv(rows, out)
    with open(out, newline="", encoding="utf-8") as f:
        read = list(csv.reader(f))
    assert read[0] == ["config", "recall", "mean_latency_ms", "repeats", "n_probes"]
    assert len(read) == 1 + len(rows)  # header + one row per config
