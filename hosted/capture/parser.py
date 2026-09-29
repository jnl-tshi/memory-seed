from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable


PARSER_VERSION = "p0.2-rules-v3-incremental"
SPACY_PIPELINE = "en_core_web_sm==3.8.0"
SAFETY_LOOKBACK_TURNS = 20
FORWARD_TURNS = 3
SPAN_WIDTH_TURNS = 3
MAX_RANKED_SPANS = 3
MAX_MESSAGES = 200
MAX_CHARACTERS = 50000
_PROPOSAL_CUES = re.compile(
    r"\b(?:i propose|we should|let'?s|use|adopt|choose|implement|the approach is|recommend)\b",
    re.IGNORECASE,
)
_AGREEMENT_CUES = re.compile(
    r"\b(?:yes|agreed|approved|that'?s the right approach|i agree|go with|choose|use|do that|would be wise)\b",
    re.IGNORECASE,
)
_REJECTION_CUES = re.compile(r"\b(?:no|reject|don'?t|do not|not that|instead)\b", re.IGNORECASE)
_TENTATIVE_CUES = re.compile(r"\b(?:maybe|might|could|possibly|consider)\b", re.IGNORECASE)
_HYPOTHETICAL_CUES = re.compile(r"\b(?:if we were to|suppose|hypothetically|imagine)\b", re.IGNORECASE)
_AMBIGUOUS_ACK = re.compile(r"^\s*(?:ok(?:ay)?|sure|fine|right|mm+[- ]?hmm)\s*[.!]?\s*$", re.IGNORECASE)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _candidate_id(rollout_id: str, source_ordinals: Iterable[int], rule_path: str, action: str) -> str:
    material = f"{rollout_id}|{','.join(str(value) for value in source_ordinals)}|{rule_path}|{action}"
    return "p02_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _clauses(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?;])\s+|\s+(?:and then|but)\s+", text.strip())
    return [part.strip(" \t\r\n.;") for part in parts if part.strip(" \t\r\n.;")]


def _selected_action(text: str) -> str:
    cleaned = re.sub(r"^(?:yes[, ]+|agreed[, ]+|i propose\s+|we should\s+|let'?s\s+)", "", text.strip(), flags=re.I)
    return cleaned[:500]


def _lexical_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_\-]{3,}", text)
        if token.lower() not in {"the", "and", "that", "this", "with", "from", "would", "should"}
    }


def _rank_spans(messages: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Rank compact spans inside the safety envelope without consulting gold evidence."""
    by_turn: dict[int, list[dict[str, Any]]] = {}
    for message in messages:
        by_turn.setdefault(int(message["turn"]), []).append(message)
    turns = sorted(by_turn)
    query_tokens = _lexical_tokens(query)
    spans: list[dict[str, Any]] = []
    for start in range(len(turns)):
        selected_turns = turns[start:start + SPAN_WIDTH_TURNS]
        if not selected_turns:
            continue
        selected = [message for turn in selected_turns for message in by_turn[turn]]
        text = "\n".join(str(message.get("text", "")) for message in selected)
        document_tokens = _lexical_tokens(text)
        lexical = len(query_tokens & document_tokens) / len(query_tokens) if query_tokens else 0.0
        score = lexical
        score += 0.08 * bool(_PROPOSAL_CUES.search(text))
        score += 0.08 * bool(_AGREEMENT_CUES.search(text))
        score += 0.04 * bool(re.search(r"\b(?:because|reason|therefore|so that|to avoid)\b", text, re.I))
        score += 0.02 * any(message.get("collaboration_mode") == "plan" for message in selected)
        spans.append({
            "turns": selected_turns,
            "source_ordinals": sorted({int(message.get("source_ordinal", -1)) for message in selected}),
            "score": round(score, 6),
        })
    spans.sort(key=lambda span: (-span["score"], -max(span["turns"]), span["turns"]))
    ranked: list[dict[str, Any]] = []
    covered: set[int] = set()
    for span in spans:
        span_turns = set(span["turns"])
        if span_turns & covered:
            continue
        ranked.append(span)
        covered.update(span_turns)
        if len(ranked) == MAX_RANKED_SPANS:
            break
    return ranked


class DecisionParser:
    def __init__(self) -> None:
        self.backend = "rules"
        try:
            import spacy  # type: ignore
            from spacy.matcher import DependencyMatcher, Matcher  # type: ignore

            self._nlp = spacy.load("en_core_web_sm")
            if spacy.__version__ != "3.8.16" or self._nlp.meta.get("version") != "3.8.0":
                raise RuntimeError("P0.2 requires spacy==3.8.16 and en_core_web_sm==3.8.0")
            self._matcher = Matcher(self._nlp.vocab)
            self._dependency_matcher = DependencyMatcher(self._nlp.vocab)
            self._matcher.add(
                "PROPOSAL_VERB",
                [[{"LEMMA": {"IN": ["propose", "recommend", "choose", "use", "adopt", "implement"]}, "POS": "VERB"}]],
            )
            self._matcher.add(
                "AGREEMENT_VERB",
                [[{"LEMMA": {"IN": ["agree", "approve", "accept", "select", "choose"]}, "POS": "VERB"}]],
            )
            self._dependency_matcher.add(
                "SUBJECT_VERB_COMPLEMENT",
                [[
                    {"RIGHT_ID": "verb", "RIGHT_ATTRS": {"POS": "VERB"}},
                    {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "subject", "RIGHT_ATTRS": {"DEP": {"IN": ["nsubj", "nsubjpass"]}}},
                    {"LEFT_ID": "verb", "REL_OP": ">", "RIGHT_ID": "complement", "RIGHT_ATTRS": {"DEP": {"IN": ["dobj", "obj", "attr", "xcomp", "ccomp"]}}},
                ]],
            )
            self.backend = SPACY_PIPELINE
        except (ImportError, OSError):
            self._nlp = None
            self._matcher = None
            self._dependency_matcher = None

    def _linguistic_rules(self, text: str) -> list[str]:
        if self._nlp is None or self._matcher is None or self._dependency_matcher is None:
            return ["regex_clause_rules"]
        document = self._nlp(text)
        rules = {self._nlp.vocab.strings[match_id].lower() for match_id, _, _ in self._matcher(document)}
        rules.update(self._nlp.vocab.strings[match_id].lower() for match_id, _ in self._dependency_matcher(document))
        return sorted(rules) or ["spacy_no_structural_match"]

    def region(
        self,
        rollout_id: str,
        messages: list[dict[str, Any]],
        *,
        marker_turn: int,
        marker: dict[str, Any] | None = None,
        lineage_messages: list[dict[str, Any]] | None = None,
        lookback_turns: int = SAFETY_LOOKBACK_TURNS,
        forward_turns: int = FORWARD_TURNS,
    ) -> dict[str, Any]:
        selected = [
            {"rollout_id": rollout_id, **message} for message in messages
            if isinstance(message.get("turn"), int)
            and marker_turn - lookback_turns <= message["turn"] <= marker_turn + forward_turns
            and (message.get("actor") in {"user", "agent"} or message.get("task_boundary")
                 or message.get("implementation_started") or message.get("decision_marker"))
        ]
        selected.extend(
            message for message in (lineage_messages or [])
            if isinstance(message.get("turn"), int) and message.get("actor") in {"user", "agent"}
        )
        selected.sort(key=lambda message: (
            str(message.get("timestamp", "")),
            str(message.get("rollout_id", rollout_id)),
            int(message.get("turn", 0)),
            int(message.get("source_ordinal", -1)),
        ))
        selected = selected[:MAX_MESSAGES]
        bounded: list[dict[str, Any]] = []
        used = 0
        for message in selected:
            text = str(message.get("text", ""))
            remaining = MAX_CHARACTERS - used
            if remaining <= 0:
                break
            clipped = text[:remaining]
            bounded.append({**message, "text": clipped})
            used += len(clipped)
        digest = hashlib.sha256(_canonical(bounded).encode("utf-8")).hexdigest()
        query = " ".join(
            value for value in (
                str(marker.get("issue_hint", "")) if marker else "",
                str(marker.get("trigger_quote", "")) if marker else "",
            ) if value
        )
        return {
            "rollout_id": rollout_id,
            "messages": bounded,
            "region_sha256": digest,
            "retrieval_strategy": "bounded_envelope_with_diagnostic_span_ranking",
            "ranked_spans": _rank_spans(bounded, query),
            "envelope_turns": sorted({int(message["turn"]) for message in bounded}),
        }

    def extract_component(self, message: dict[str, Any]) -> dict[str, Any]:
        from .incremental import extract_component
        return extract_component(self, message)

    def parse(
        self, rollout_id: str, messages: list[dict[str, Any]], *,
        marker: dict[str, Any] | None = None,
        lineage_messages: list[dict[str, Any]] | None = None,
        lookback_turns: int = SAFETY_LOOKBACK_TURNS,
        forward_turns: int = FORWARD_TURNS,
    ) -> list[dict[str, Any]]:
        from .incremental import ExtractionState
        if not messages:
            return []
        turn = int(marker["turn"]) if marker else int(messages[-1].get("turn", 0))
        region = self.region(rollout_id, messages, marker_turn=turn, marker=marker,
                             lineage_messages=lineage_messages,
                             lookback_turns=lookback_turns, forward_turns=forward_turns)
        state = ExtractionState(self, rollout_id)
        state.feed(region["messages"])
        return state.assemble(marker)

    @staticmethod
    def _candidate_is_complete(candidate: dict[str, Any], marker: dict[str, Any]) -> bool:
        return bool(candidate.get("complete") and candidate.get("state") == "accepted")

    def parse_stepped(
        self, rollout_id: str, messages: list[dict[str, Any]], *,
        marker: dict[str, Any],
        lineage_messages: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Replay available evidence; NLP sees each coordinate at most once.

        The caller supplies only observed events. Earlier context can resolve an
        anchor; future turns are revealed one turn at a time, never eagerly.
        State is scoped to this call; durable incremental subscriptions are not
        yet implemented.
        """
        from .incremental import ExtractionState, coordinate, utc_time
        state = ExtractionState(self, rollout_id)
        visible = [{"rollout_id": rollout_id, **m} for m in messages
                   if m.get("actor") in {"user", "agent"} or m.get("task_boundary")
                   or m.get("implementation_started") or m.get("decision_marker")]
        visible.sort(key=lambda m: int(m['source_ordinal']))
        anchors = [m for m in visible if m["rollout_id"] == rollout_id
                   and m.get("turn") == marker["turn"]
                   and ("source_ordinal" not in marker or m.get("source_ordinal") == marker["source_ordinal"])
                   and marker.get("trigger_quote")
                   and marker["trigger_quote"] in str(m.get("text", ""))]
        if len(anchors) != 1:
            return []
        anchor = anchors[0]
        anchor_index = visible.index(anchor)
        marker_turn = int(marker["turn"])
        history = visible[:anchor_index]
        # Task/decision boundaries bound historical lookup as well as forward reads.
        boundaries = [i for i, m in enumerate(history)
                      if m.get("task_boundary") or m.get("decision_marker")]
        if boundaries:
            history = history[max(boundaries) + 1:]
        future = visible[anchor_index + 1:]
        stages = [("marker", [anchor])]
        for back in (1, 3, 5, 12, 20):
            stages.append((f"backward_{back}", [
                m for m in history if marker_turn - back <= int(m["turn"]) <= marker_turn]))
        # Cross-rollout chronology must be explicit; missing timestamps abstain.
        parents = [m for m in (lineage_messages or [])
                   if utc_time(m) and utc_time(anchor)
                   and utc_time(m) <= utc_time(anchor)]
        if parents and not boundaries:
            stages.append(("lineage_safety_envelope", parents))
        stop_reason = "available_evidence_exhausted"
        for turn in sorted({int(m["turn"]) for m in future
                            if int(m["turn"]) <= marker_turn + 20}):
            delta = []
            boundary = False
            for message in [m for m in future if int(m["turn"]) == turn]:
                if (message.get("task_boundary") or message.get("decision_marker")
                        or message.get("implementation_started")):
                    boundary = True
                    stop_reason = "lifecycle_boundary_requires_new_decision"
                    break
                delta.append(message)
            if delta:
                stages.append((f"forward_{turn - marker_turn}", delta))
            if boundary:
                break
        attempts: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        used_chars = 0
        for stage, offered in stages:
            delta = []
            for raw in offered:
                message = {"rollout_id": rollout_id, **raw}
                if coordinate(message) in state.components:
                    continue
                size = len(str(message.get("text", "")))
                if len(state.components) + len(delta) >= MAX_MESSAGES or used_chars + size > MAX_CHARACTERS:
                    stop_reason = "budget_exhausted"
                    continue  # never clip evidence into a different assertion
                delta.append(message)
                used_chars += size
            if not delta:
                continue
            before = state.extraction_calls
            state.feed(delta)
            candidates = state.assemble(marker)
            complete = [c for c in candidates if self._candidate_is_complete(c, marker)]
            attempts.append({"stage": stage, "delta_messages": state.extraction_calls - before,
                             "delta_characters": sum(len(str(m.get("text", ""))) for m in delta),
                             "cumulative_messages": len(state.components),
                             "complete_candidates": len(complete)})
            if complete:
                candidates = complete
                stop_reason = "complete"
                break
        for candidate in candidates:
            candidate["source"]["retrieval_trace"] = {
                "selected_stage": attempts[-1]["stage"] if attempts else "none",
                "forward_turns": max([int(a["stage"].split("_")[1]) for a in attempts
                                      if a["stage"].startswith("forward_")] or [0]),
                "messages_used": len(state.components), "characters_used": used_chars,
                "total_messages_processed": state.extraction_calls, "attempts": attempts,
                "fallback_used": any(a["stage"] == "lineage_safety_envelope" for a in attempts),
                "stop_reason": stop_reason,
            }
        return candidates
