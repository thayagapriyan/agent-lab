"""The fixed probe set — the lab's measuring stick (ADR-004).

A probe is a ``(seed, question, expected)`` triple:

* **seed**     — a fact planted in an early turn ("My favorite fruit is mango.")
* **question** — a later turn that probes recall ("What is my favorite fruit?")
* **expected** — keyword(s) that mark a correct answer ("mango"); the answer is
  recalled if it contains at least one (case-insensitive — see ``scoring.score``).

This set is **fixed** (ADR-004): it is a teaching instrument, not a benchmark.
Editing it creates a *new baseline* — say so loudly and re-run prior configs.
Keep it small, hand-written, and varied across the kinds of facts the semantic
strategy should capture (preference, identity, name, constraint, place, number).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Probe:
    """One recall test: plant ``seed``, later ask ``question``, expect ``expected``.

    ``expected`` is a tuple of acceptable keywords; the answer is correct if it
    contains ANY of them (case-insensitive substring — see ``scoring.score``). A
    tuple, not a single string, so a fact with valid variants ("biologist" /
    "marine biologist") matches without loosening the scorer.
    """

    seed: str
    question: str
    expected: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.seed.strip():
            raise ValueError("Probe.seed must be non-empty")
        if not self.question.strip():
            raise ValueError("Probe.question must be non-empty")
        if not self.expected or any(not k.strip() for k in self.expected):
            raise ValueError("Probe.expected must be a non-empty tuple of non-empty keywords")


# The fixed probe set. ORDER AND CONTENT ARE STABLE (ADR-004): changing it is a
# new baseline, not an edit. Six probes across distinct fact *types* so a strategy
# that captures one kind (e.g. preferences) but misses another (e.g. numbers) shows
# up as a partial recall score rather than all-or-nothing.
PROBES: tuple[Probe, ...] = (
    Probe(
        seed="My favorite fruit is mango.",
        question="What is my favorite fruit?",
        expected=("mango",),
    ),
    Probe(
        seed="I work as a marine biologist.",
        question="What is my job?",
        expected=("marine biologist", "biologist"),
    ),
    Probe(
        seed="My dog's name is Pixel.",
        question="What is my dog called?",
        expected=("pixel",),
    ),
    Probe(
        seed="I'm allergic to peanuts.",
        question="Is there a food I should avoid?",
        expected=("peanut", "peanuts"),
    ),
    Probe(
        seed="I live in Lisbon.",
        question="Which city do I live in?",
        expected=("lisbon",),
    ),
    Probe(
        seed="My favorite number is 42.",
        question="What is my favorite number?",
        expected=("42", "forty-two"),
    ),
)


def load_probes() -> tuple[Probe, ...]:
    """Return the fixed probe set.

    A function (not just the module constant) gives later code a single seam to
    deliberately swap in a different set — which, per ADR-004, is a new baseline.
    """
    return PROBES
