from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable


PARSER_VERSION = "p0.2-rules-v1"
SPACY_PIPELINE = "en_core_web_sm==3.8.0"
MAX_MESSAGES = 20
MAX_CHARACTERS = 8000
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


class DecisionParser:
    def __init__(self) -> None:
        self.backend = "rules"
        try:
            import spacy  # type: ignore
            from spacy.matcher import DependencyMatcher, Matcher  # type: ignore

            self._nlp = spacy.load("en_core_web_sm")
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
    ) -> dict[str, Any]:
        selected = [
            message for message in messages
            if isinstance(message.get("turn"), int)
            and marker_turn - 2 <= message["turn"] <= marker_turn + 1
            and message.get("actor") in {"user", "agent"}
        ][:MAX_MESSAGES]
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
        return {"rollout_id": rollout_id, "messages": bounded, "region_sha256": digest}

    def parse(
        self,
        rollout_id: str,
        messages: list[dict[str, Any]],
        *,
        marker: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not messages:
            return []
        marker_turn = int(marker["turn"]) if marker and isinstance(marker.get("turn"), int) else int(messages[-1].get("turn", 0))
        region = self.region(rollout_id, messages, marker_turn=marker_turn)
        visible = region["messages"]
        marker_quote = str(marker.get("trigger_quote", "")) if marker else ""
        proposals = [message for message in visible if _PROPOSAL_CUES.search(str(message.get("text", "")))]
        if marker and marker.get("issue_hint") and not proposals:
            proposals = [message for message in visible if message.get("actor") in {"user", "agent"}][-1:]
        candidates: list[dict[str, Any]] = []
        for proposal in proposals:
            proposal_text = str(proposal.get("text", ""))
            if _HYPOTHETICAL_CUES.search(proposal_text):
                continue
            agreement = None
            rejection = None
            for message in visible:
                if message.get("actor") != "user" or int(message.get("source_ordinal", -1)) <= int(proposal.get("source_ordinal", -1)):
                    continue
                text = str(message.get("text", ""))
                if _AMBIGUOUS_ACK.match(text):
                    continue
                if _REJECTION_CUES.search(text):
                    rejection = message
                if marker_quote and marker_quote in text:
                    agreement = message
                    break
                if _AGREEMENT_CUES.search(text) and not _TENTATIVE_CUES.search(text):
                    agreement = message
                    break
            if marker and marker.get("state") == "accepted" and agreement is None:
                continue
            state = "accepted" if agreement is not None and rejection is None else "proposed"
            if rejection is not None:
                state = "rejected"
            action_source = agreement if agreement is not None else proposal
            action = _selected_action(str(action_source.get("text", "")))
            quote = marker_quote if marker_quote and agreement is not None else (
                _AGREEMENT_CUES.search(str(agreement.get("text", ""))).group(0) if agreement and _AGREEMENT_CUES.search(str(agreement.get("text", ""))) else None
            )
            rule_path = "marker>proposal>grounded_agreement" if marker and state == "accepted" else (
                "cue>proposal>grounded_agreement" if state == "accepted" else "cue>proposal"
            )
            ordinals = [int(proposal.get("source_ordinal", 0))]
            if agreement is not None:
                ordinals.append(int(agreement.get("source_ordinal", 0)))
            reasons = [clause for clause in _clauses(proposal_text) if re.search(r"\b(?:because|so that|to avoid|therefore)\b", clause, re.I)]
            conditions = [clause for clause in _clauses(proposal_text) if re.search(r"\b(?:if|unless|when|only)\b", clause, re.I)]
            candidates.append(
                {
                    "candidate_id": _candidate_id(rollout_id, ordinals, rule_path, action),
                    "schema_version": "p0.2-draft-v1",
                    "parser_version": PARSER_VERSION,
                    "parser_backend": self.backend,
                    "state": state,
                    "issue": str(marker.get("issue_hint")) if marker else None,
                    "proposal": proposal_text,
                    "selected_action": action,
                    "agreement_quote": quote,
                    "reason": reasons[0] if reasons else None,
                    "conditions": conditions,
                    "modality": "tentative" if _TENTATIVE_CUES.search(proposal_text) else "committed" if state == "accepted" else "proposed",
                    "negated": rejection is not None,
                    "rejected_alternatives": [str(rejection.get("text"))] if rejection else [],
                    "deciding_actor": "user" if agreement is not None else str(proposal.get("actor", "unknown")),
                    "source": {
                        "rollout_id": rollout_id,
                        "source_ordinals": sorted(set(ordinals)),
                        "region_sha256": region["region_sha256"],
                        "messages": visible,
                    },
                    "rule_path": rule_path,
                    "linguistic_rules": self._linguistic_rules(proposal_text),
                    "authoritative": False,
                    "curator_verification_required": True,
                }
            )
        unique = {candidate["candidate_id"]: candidate for candidate in candidates}
        return [unique[key] for key in sorted(unique)]
