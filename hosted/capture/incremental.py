"""Conservative, inert decision drafts from retained per-message components.

Retrieval can add older evidence out of order. Linguistic extraction occurs once
per source coordinate; assembly may revisit cached components, never raw NLP.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


ACTION = re.compile(r"\b(?:use|adopt|choose|implement|keep|retain|stop|process|capture)\b[^.!?;]+", re.I)
PROPOSAL = re.compile(r"\b(?:i propose|we should|let's|recommend)\b", re.I)
AGREEMENT = re.compile(r"\b(?:yes|agreed|approved|i agree|that's the right approach|do that)\b", re.I)
TENTATIVE = re.compile(r"\b(?:maybe|might|could|possibly|consider|if we were|suppose|hypothetically|imagine)\b", re.I)
REJECT = re.compile(r"\b(?:no|reject|don't|do not|not that)\b", re.I)
REFERENCE = re.compile(r"\b(?:that approach|this approach|do that|use it|adopt it|option [a-z0-9]+)\b", re.I)
SCOPE = re.compile(r"\b(?:for|within|in)\s+([^.!?;]+)", re.I)
ISSUE = re.compile(r"\b(?:issue\s*:|problem\s*:|we need to choose)\s*([^.!?;]+)", re.I)


def coordinate(message: dict[str, Any]) -> tuple[str, int, int]:
    return (str(message['rollout_id']), int(message['turn']), int(message['source_ordinal']))


def order(message: dict[str, Any]) -> tuple:
    return (utc_time(message) or datetime.min.replace(tzinfo=timezone.utc), *coordinate(message))


def utc_time(message: dict) -> datetime | None:
    try:
        value = datetime.fromisoformat(str(message.get('timestamp', '')).replace('Z', '+00:00'))
        return value.astimezone(timezone.utc) if value.tzinfo else None
    except ValueError:
        return None


def ordered_components(components: list[dict]) -> list[dict]:
    # Merge rollout streams while preserving authoritative per-rollout ordinals.
    streams: dict[str, list[dict]] = {}
    for component in components:
        streams.setdefault(component['message']['rollout_id'], []).append(component)
    for stream in streams.values():
        stream.sort(key=lambda c: c['message']['source_ordinal'])
    result = []
    while streams:
        rollout = min(streams, key=lambda r: order(streams[r][0]['message']))
        result.append(streams[rollout].pop(0))
        if not streams[rollout]:
            del streams[rollout]
    return result


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


class ExtractionState:
    def __init__(self, parser: Any, rollout_id: str):
        self.parser = parser
        self.rollout_id = rollout_id
        self.components: dict[tuple, dict] = {}
        self.extraction_calls = 0

    def feed(self, messages: list[dict]) -> int:
        count = 0
        for raw in messages:
            message = {'rollout_id': self.rollout_id, **raw}
            key = coordinate(message)
            if key in self.components:
                if self.components[key]['message'] != message:
                    raise ValueError('source coordinate changed content')
                continue
            self.components[key] = self.parser.extract_component(message)
            self.extraction_calls += 1
            count += 1
        return count

    def assemble(self, marker: dict | None = None) -> list[dict]:
        from .parser import PARSER_VERSION

        components = ordered_components(list(self.components.values()))
        messages = [c['message'] for c in components]
        anchor = None
        if marker:
            matches = [c for c in components if c['message']['rollout_id'] == self.rollout_id
                       and c['message']['turn'] == marker['turn']
                       and ('source_ordinal' not in marker or c['message']['source_ordinal'] == marker['source_ordinal'])
                       and marker.get('trigger_quote')
                       and marker['trigger_quote'] in str(c['message'].get('text', ''))]
            if len(matches) != 1:
                return []  # exact source validation; a breadcrumb is not acceptance
            anchor = matches[0]
        candidates = []
        for index, proposal in enumerate(components):
            if not proposal['proposal'] or proposal['excluded']:
                continue
            agreement = proposal if proposal['commitment'] else None
            rejected = None
            for later in components[index + 1:]:
                if later['boundary']:
                    break
                if later['excluded']:
                    continue
                if '?' in str(later['message'].get('text', '')):
                    break  # a later acknowledgement may answer this different question
                if later['proposal']:
                    break  # ambiguous multiple proposals, or a new decision
                if later['message']['actor'] == 'user':
                    if later['rejected']:
                        rejected = later
                        break
                    cross_rollout = later['message']['rollout_id'] != proposal['message']['rollout_id']
                    causal = not cross_rollout or (utc_time(later['message']) is not None
                             and utc_time(proposal['message']) is not None
                             and utc_time(proposal['message']) <= utc_time(later['message']))
                    if later['agreement'] and causal:
                        agreement = later
                        break
            if marker and anchor not in (proposal, agreement, rejected):
                continue
            state = 'rejected' if rejected else 'accepted' if agreement else 'proposed'
            evidence = [proposal]
            for component in (agreement, rejected):
                if component and component not in evidence:
                    evidence.append(component)
            sources = [c['message'] for c in evidence]
            action = proposal['action']
            scope = proposal['scope']
            issue_component = proposal if proposal['issue'] else None
            for prior in reversed(components[:index]):
                if issue_component or prior['boundary'] or prior['proposal']:
                    break
                if prior['issue'] and not prior['excluded']:
                    issue_component = prior
            issue = issue_component['issue'] if issue_component else None
            if issue_component and issue_component not in evidence:
                sources.insert(0, issue_component['message'])
            missing = [name for name, value in [('issue', issue), ('chosen_action', action),
                       ('scope', scope), ('grounded_acceptance', agreement)] if not value]
            if proposal['unresolved']:
                missing.append('resolved_references')
            coords = [dict(zip(('rollout_id', 'turn', 'source_ordinal'), coordinate(m))) for m in sources]
            path = ('marker' if marker else 'cue') + '>cached_clause>' + state
            identity = canonical({'coordinates': coords, 'action': action, 'rule': path})
            quote = agreement['message']['text'] if agreement else None
            if agreement is anchor and marker:
                quote = marker['trigger_quote']
            candidates.append({
                'candidate_id': 'p02_' + hashlib.sha256(identity.encode()).hexdigest()[:24],
                'schema_version': 'p0.2-draft-v2', 'parser_version': PARSER_VERSION,
                'parser_backend': self.parser.backend, 'state': state,
                'issue': issue, 'issue_hint': marker.get('issue_hint') if marker else None,
                'scope': scope, 'proposal': proposal['message']['text'], 'selected_action': action,
                'agreement_quote': quote, 'reason': proposal['reason'], 'conditions': proposal['conditions'],
                'modality': 'committed' if agreement else 'proposed', 'negated': bool(rejected),
                'rejected_alternatives': [rejected['message']['text']] if rejected else [],
                'deciding_actor': 'user' if agreement else proposal['message']['actor'],
                'complete': not missing, 'missing_components': missing,
                'rule_path': path, 'linguistic_rules': proposal['linguistic_rules'],
                'authoritative': False, 'curator_verification_required': True,
                'source': {'rollout_id': self.rollout_id, 'source_coordinates': coords,
                           'source_ordinals': sorted({m['source_ordinal'] for m in sources}),
                           'messages': messages, 'envelope_turns': sorted({m['turn'] for m in messages}),
                           'region_sha256': hashlib.sha256(canonical(messages).encode()).hexdigest(),
                           'retrieval_strategy': 'delta_only_components'},
            })
        return sorted(candidates, key=lambda c: c['candidate_id'])


def extract_component(parser: Any, message: dict) -> dict:
    text = str(message.get('text', ''))
    # Replay/history annotations and quoted material are not live instructions.
    excluded = bool(message.get('copied_history') or message.get('post_hoc_record')
                    or text.lstrip().startswith(('>', '```')) or TENTATIVE.search(text))
    rejected = bool(REJECT.search(text))
    match = ACTION.search(ISSUE.sub('', text))
    action = match.group(0).strip().rstrip('.') if match else None
    action = re.split(r'\s+because\s+', action, maxsplit=1, flags=re.I)[0] if action else None
    scope_match = SCOPE.search(action or '')
    scope = scope_match.group(1).strip() if scope_match else None
    imperative = bool(re.match(r"^(?:(?:yes|agreed)[,!. ]+)?(?:use|adopt|choose|implement|keep|retain|stop|process|capture)\b", text.strip(), re.I))
    issue = ISSUE.search(text)
    if issue and match:
        imperative = bool(re.search(r'[.!;]\s*(?:Use|Adopt|Choose|Implement|Keep|Retain|Stop|Process|Capture)\b', text, re.I))
    commitment = bool(message.get('actor') == 'user' and imperative and action and not rejected
                      and not excluded and '?' not in text and not PROPOSAL.search(text))
    proposal = bool(imperative or PROPOSAL.search(text)) and '?' not in text
    # A pure contextual agreement never supplies its own chosen action.
    if action and re.fullmatch(r'(?:use it|do that)', action, re.I):
        proposal = False
    reason = re.search(r'\bbecause\s+([^.!?]+)', text, re.I)
    return {'message': message, 'action': action, 'scope': scope,
            'issue': issue.group(1).strip() if issue else None,
            'proposal': proposal, 'commitment': commitment,
            'agreement': bool(AGREEMENT.search(text)) and not rejected and not excluded,
            'rejected': rejected, 'excluded': excluded,
            'unresolved': bool(REFERENCE.search(action or text)),
            'reason': reason.group(1) if reason else None,
            'conditions': re.findall(r'\b(?:if|unless|when|only)\s+[^.!?;]+', text, re.I),
            'boundary': bool(message.get('task_boundary') or message.get('decision_marker')
                             or message.get('implementation_started')),
            'linguistic_rules': parser._linguistic_rules(text)}
