"""Deterministic, provider-independent historical source disclosure."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


MAX_PRECEDING_TURNS = 20
MAX_EXPANSIONS = 10
MAX_SOURCE_CHARACTERS = 50_000


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be JSON-compatible") from exc


class AdaptiveDisclosure:
    """Disclose the anchor turn, then at most twenty preceding turns in pairs.

    ``anchor`` is ``(rollout_id, turn, source_ordinal)``. Every batch remains
    available in ``batches``; callers can transmit only the most recent batch.
    """

    def __init__(self, messages: list[dict], anchor: tuple[str, int, int] | dict):
        if not isinstance(messages, list):
            raise ValueError("messages must be a finite list")
        if isinstance(anchor, dict):
            try:
                anchor = (anchor["rollout_id"], anchor["turn"], anchor["source_ordinal"])
            except KeyError as exc:
                raise ValueError("anchor requires rollout_id, turn, and source_ordinal") from exc
        if not isinstance(anchor, (tuple, list)) or len(anchor) != 3:
            raise ValueError("anchor must be (rollout_id, turn, source_ordinal)")
        rollout, turn, ordinal = anchor
        if not isinstance(rollout, str) or not rollout or type(turn) is not int or turn < 0 or type(ordinal) is not int or ordinal < 0:
            raise ValueError("invalid anchor coordinate")
        self.anchor = (rollout, turn, ordinal)
        self._messages: dict[tuple[str, int, int], dict] = {}
        for raw in messages:
            if not isinstance(raw, dict):
                raise ValueError("each message must be an object")
            msg = deepcopy(raw)
            if msg.get("rollout_id") != rollout:
                raise ValueError("all messages must belong to the anchor rollout")
            if type(msg.get("turn")) is not int or msg["turn"] < 0 or type(msg.get("source_ordinal")) is not int or msg["source_ordinal"] < 0:
                raise ValueError("turn and source_ordinal must be nonnegative integers")
            if not isinstance(msg.get("actor"), str) or not msg["actor"] or not isinstance(msg.get("text"), str):
                raise ValueError("message requires actor and text strings")
            _canonical(msg)
            coord = (rollout, msg["turn"], msg["source_ordinal"])
            if coord in self._messages:
                raise ValueError("repeated source coordinate")
            self._messages[coord] = msg
        if self.anchor not in self._messages:
            raise ValueError("anchor coordinate is not present in messages")
        # Source after the anchor coordinate is outside this immutable view.
        self._messages = {c: m for c, m in self._messages.items() if (c[1], c[2]) <= (turn, ordinal)}
        self._batches: list[dict] = []
        self._usage: dict[int, tuple[int, int]] = {}
        self._cursor = turn - 1
        self.expansion_calls = 0
        self.questions_complete = False
        self.stop_reason: str | None = None
        self._total_chars = 0
        self._disclosed: set[tuple[str, int, int]] = set()
        if not self._append_batch([turn]):
            self.stop_reason = "character_budget"

    def _append_batch(self, turns: list[int]) -> bool:
        selected = [(c, m) for c, m in self._messages.items() if c[1] in turns and c not in self._disclosed]
        selected.sort(key=lambda pair: (pair[0][1], pair[0][2]))
        chars = sum(len(m["text"]) for _, m in selected)
        if self._total_chars + chars > MAX_SOURCE_CHARACTERS:
            return False
        material = {"index": len(self._batches), "turns": turns, "messages": [m for _, m in selected], "source_characters": chars}
        digest = hashlib.sha256(_canonical(material).encode("utf-8")).hexdigest()
        self._total_chars += chars
        self._disclosed.update(c for c, _ in selected)
        self._batches.append({**material, "cumulative_source_characters": self._total_chars, "digest": digest})
        return True

    @property
    def batches(self) -> list[dict]:
        """A detached snapshot of every disclosed batch."""
        return deepcopy(self._batches)

    def mark_questions_complete(self) -> None:
        self.questions_complete = True
        if self.stop_reason in (None, "session_start", "window_exhausted"):
            self.stop_reason = "answered_all_questions"

    def expand(self) -> dict | None:
        if self.stop_reason is not None:
            return None
        if self.questions_complete:
            self.stop_reason = "answered_all_questions"
            return None
        if self.expansion_calls >= MAX_EXPANSIONS:
            self.stop_reason = "window_exhausted"
            return None
        if self._cursor < max(0, self.anchor[1] - MAX_PRECEDING_TURNS):
            self.stop_reason = "session_start" if self._cursor < 0 else "window_exhausted"
            return None
        lower_bound = max(0, self.anchor[1] - MAX_PRECEDING_TURNS)
        upper = self._cursor
        lower = max(lower_bound, upper - 1)
        turns = list(range(lower, upper + 1))
        if not self._append_batch(turns):
            self.stop_reason = "character_budget"
            return None
        self.expansion_calls += 1
        self._cursor = lower - 1
        # Stop immediately when this pair reached a natural boundary.
        if self._cursor < lower_bound:
            self.stop_reason = "session_start" if lower_bound == 0 and self._cursor < 0 else "window_exhausted"
        return deepcopy(self._batches[-1])

    def record_usage(self, batch_index: int, prompt_tokens: int, completion_tokens: int) -> None:
        for value in (batch_index, prompt_tokens, completion_tokens):
            if type(value) is not int or value < 0:
                raise ValueError("batch index and token counts must be nonnegative integers")
        if batch_index >= len(self.batches):
            raise ValueError("usage references an unknown batch")
        usage = (prompt_tokens, completion_tokens)
        if batch_index in self._usage and self._usage[batch_index] != usage:
            raise ValueError("conflicting usage for batch")
        self._usage[batch_index] = usage

    def summary(self) -> dict:
        return {
            "prompt_tokens": sum(v[0] for v in self._usage.values()),
            "completion_tokens": sum(v[1] for v in self._usage.values()),
            "disclosed_source_messages": len(self._disclosed),
            "disclosed_source_characters": self._total_chars,
            "expansion_calls": self.expansion_calls,
            "stop_reason": self.stop_reason,
        }

    def to_dict(self) -> dict:
        return {"anchor": {"rollout_id": self.anchor[0], "turn": self.anchor[1], "source_ordinal": self.anchor[2]}, "batches": deepcopy(self._batches), "summary": self.summary()}
