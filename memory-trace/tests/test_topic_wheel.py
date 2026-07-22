"""The colour wheel: co-occurring topics must sit adjacent, deterministically.

The wheel exists so the renderer can hand out hues where related communities
are colour NEIGHBOURS, and so a multi-topic node's mixed colour stays
in-family. The properties that matter are pinned here; the exact order is not,
because it is corpus-derived.
"""

from __future__ import annotations

from memory_trace.service import _seriate_circle


def _adjacent_weight(order: list[str], weight: dict[tuple[str, str], int]) -> int:
    def w(a: str, b: str) -> int:
        return weight.get((min(a, b), max(a, b)), 0)

    return sum(w(order[i], order[(i + 1) % len(order)]) for i in range(len(order)))


def test_heavily_co_occurring_topics_end_up_adjacent() -> None:
    # Two tight families joined by nothing: each family must occupy a
    # contiguous arc, which is the whole point of the wheel.
    weight = {
        ("a1", "a2"): 50, ("a2", "a3"): 40, ("a1", "a3"): 30,
        ("b1", "b2"): 45, ("b2", "b3"): 35, ("b1", "b3"): 25,
    }
    order = _seriate_circle(["a1", "a2", "a3", "b1", "b2", "b3"], weight)
    positions = {topic: index for index, topic in enumerate(order)}
    a = sorted(positions[t] for t in ("a1", "a2", "a3"))
    assert a[2] - a[0] == 2, f"family A must be a contiguous arc, got {order}"


def test_the_wheel_is_deterministic() -> None:
    weight = {("x", "y"): 3, ("y", "z"): 2, ("w", "x"): 1}
    items = ["w", "x", "y", "z"]
    assert _seriate_circle(list(items), dict(weight)) == _seriate_circle(list(items), dict(weight))


def test_no_co_occurrence_at_all_still_yields_a_stable_order() -> None:
    # A corpus of single-topic entries has zero pair weights; the wheel must
    # not crash or vary - alphabetical tie-breaks carry it.
    order = _seriate_circle(["c", "a", "b"], {})
    assert sorted(order) == ["a", "b", "c"]
    assert order == _seriate_circle(["b", "c", "a"], {})


def test_seriation_beats_the_alphabetical_circle_it_replaced() -> None:
    # The measured motivation, in miniature: alphabetical order separates the
    # heavy pair, the seriated wheel must not.
    weight = {("aardvark", "zebra"): 100, ("aardvark", "middle"): 1}
    order = _seriate_circle(["aardvark", "middle", "zebra"], weight)
    alphabetical = ["aardvark", "middle", "zebra"]
    assert _adjacent_weight(order, weight) >= _adjacent_weight(alphabetical, weight)
    positions = {t: i for i, t in enumerate(order)}
    gap = abs(positions["aardvark"] - positions["zebra"])
    assert gap in (1, len(order) - 1), "the 100-weight pair must be adjacent on the circle"


def test_tiny_wheels_pass_through() -> None:
    assert _seriate_circle(["a"], {}) == ["a"]
    assert _seriate_circle(["b", "a"], {}) == ["b", "a"]
