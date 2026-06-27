"""Iteration 4 tests: the fixed probe set + the keyword scorer + the runner.

All offline (no AWS, no cost), mirroring the smoke/memory tests' philosophy. These
prove the measuring instrument itself is correct and deterministic — the thing the
Iteration 5 sweep relies on being identical across every run.
"""

from __future__ import annotations

import pytest

from probes import PROBES, Probe, ProbeResult, load_probes, run_probe, score


# --- The probe set: fixed, well-formed (ADR-004) ------------------------------

def test_probe_set_is_nonempty_and_wellformed():
    probes = load_probes()
    assert probes is PROBES and len(probes) >= 1
    for p in probes:
        assert p.seed.strip() and p.question.strip()
        assert p.expected and all(k.strip() for k in p.expected)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seed": "   "},                       # empty seed
        {"question": ""},                       # empty question
        {"expected": ()},                       # no keywords
        {"expected": ("ok", " ")},              # a blank keyword
    ],
)
def test_probe_rejects_malformed(kwargs):
    base = dict(seed="s", question="q", expected=("k",))
    with pytest.raises(ValueError):
        Probe(**{**base, **kwargs})


# --- The scorer: keyword/substring, case-insensitive, any-match (ADR-006) -----

def test_score_matches_case_insensitive_substring():
    assert score("You should order the MANGO smoothie.", ("mango",)) is True


def test_score_any_keyword_matches():
    assert score("You're a biologist.", ("marine biologist", "biologist")) is True


def test_score_returns_false_when_absent():
    assert score("I have no idea.", ("mango",)) is False


def test_score_is_deterministic():
    # Same inputs -> same output, every time (the sweep depends on this).
    answer, expected = "It's Lisbon.", ("lisbon",)
    assert score(answer, expected) == score(answer, expected) is True


# --- The runner: seed -> question -> time -> score ----------------------------

class _FakeAgent:
    """Records prompts it receives and returns a canned reply (no network)."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


def test_run_probe_seeds_then_questions_and_scores_correct():
    probe = Probe(seed="My favorite fruit is mango.", question="fav fruit?", expected=("mango",))
    agent = _FakeAgent("Your favorite fruit is mango.")

    result = run_probe(probe, agent)

    assert isinstance(result, ProbeResult)
    assert agent.prompts == [probe.seed, probe.question]  # seed first, then question
    assert result.correct is True
    assert result.answer == "Your favorite fruit is mango."
    assert result.latency_ms >= 0.0


def test_run_probe_marks_incorrect_when_not_recalled():
    probe = Probe(seed="My favorite fruit is mango.", question="fav fruit?", expected=("mango",))
    result = run_probe(probe, _FakeAgent("I don't remember."))
    assert result.correct is False


def test_run_probe_uses_separate_question_agent_for_cross_session():
    # The long-term path: seed on one agent, ask on another (new session, same actor).
    probe = Probe(seed="I live in Lisbon.", question="which city?", expected=("lisbon",))
    seed_agent = _FakeAgent("noted")
    question_agent = _FakeAgent("You live in Lisbon.")

    result = run_probe(probe, seed_agent, question_agent=question_agent)

    assert seed_agent.prompts == [probe.seed]          # seed went to the seed agent only
    assert question_agent.prompts == [probe.question]  # question went to the other agent only
    assert result.correct is True
