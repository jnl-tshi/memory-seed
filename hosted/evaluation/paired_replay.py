"""Frozen, owner-local paired replay. Gold is scoring data, never parser input."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import types
from collections import Counter
from pathlib import Path

from hosted.capture import incremental
from hosted.capture.corpus import build_manifest
from hosted.capture.evaluation import _load_alignment_parser, _rollout_paths, _record_text
from hosted.capture.parser import DecisionParser

BASELINE = '1c3f2e298e95ae8c54dcc5918cbaf6d2e95e3003'
REVISED = '95514648be7dae6652d217fd8bfbcade897e19d3'
CUE = re.compile(r"\b(?:yes|agreed|approved|i agree|use|adopt|choose|i propose|we should|let's|recommend)\b", re.I)
AGREEMENT = re.compile(r"\b(?:yes|agreed|approved|i agree|use|adopt|choose)\b", re.I)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha(value: bytes):
    return hashlib.sha256(value).hexdigest()


def coordinate(row):
    return str(row['rollout_id']).lower(), int(row['turn']), int(row['source_ordinal'])


def causal_prefix(messages, anchor):
    return sorted([m for m in messages if m['rollout_id'] == anchor['rollout_id']
                   and m['source_ordinal'] <= anchor['source_ordinal']],
                  key=lambda m: m['source_ordinal'])


def coverage(refs, messages):
    return bool(refs) and {coordinate(r) for r in refs}.issubset({coordinate(m) for m in messages})


def cue_marker(message, *, oracle=False):
    text = str(message.get('text', ''))
    match = CUE.search(text)
    if not match and not oracle:
        return None
    accepted = message.get('actor') == 'user' and bool(AGREEMENT.search(text))
    return dict(turn=message['turn'], source_ordinal=message['source_ordinal'],
                strength='hard' if accepted else 'soft', state='accepted' if accepted else 'proposed',
                origin='user' if message.get('actor') == 'user' else 'agent',
                trigger_class='contextual_acceptance' if accepted else 'agent_inference',
                issue_hint='observed decision signal', trigger_quote=match.group(0) if match else text[:160])


def baseline_parser(repo):
    raw = subprocess.check_output(['git', 'show', f'{BASELINE}:hosted/capture/parser.py'], cwd=repo)
    module = types.ModuleType('frozen_p02_legacy')
    exec(compile(raw, f'{BASELINE}:hosted/capture/parser.py', 'exec'), module.__dict__)
    return module.DecisionParser(), sha(raw)


def normalize_ablation(drafts):
    result = json.loads(encoded(drafts))
    for draft in result:
        trace = draft.get('source', {}).get('retrieval_trace', {})
        trace.pop('total_messages_processed', None)
        for attempt in trace.get('attempts', []):
            attempt.pop('delta_messages', None)
    return result


def replay_revised(parser, rollout, current, marker, parents, *, recompute=False):
    original = incremental.ExtractionState
    instances = []

    class MeasuredState(original):
        def __init__(self, *args):
            super().__init__(*args)
            self.characters_processed = 0
            instances.append(self)

        def feed(self, messages):
            if recompute:
                messages = [c['message'] for c in self.components.values()] + messages
                self.components = {}
            self.characters_processed += sum(len(str(m.get('text', ''))) for m in messages)
            return super().feed(messages)

    incremental.ExtractionState = MeasuredState
    try:
        drafts = parser.parse_stepped(rollout, current, marker=marker, lineage_messages=parents)
    finally:
        incremental.ExtractionState = original
    state = instances[0]
    return drafts, {'extraction_calls': state.extraction_calls,
                    'characters_processed': state.characters_processed}, [c['message'] for c in state.components.values()]


def public_case(row):
    return {key: value for key, value in row.items() if key not in {'review', 'raw_drafts'}}


def validated_gold_text(repo, row):
    """Reject stale gold line ranges instead of scoring a neighbouring record."""
    record = row['record']
    lines = (repo / record['path']).read_text(encoding='utf-8').splitlines()
    start, end = int(record['start_line']), int(record['end_line'])
    if not 1 <= start <= end <= len(lines):
        raise ValueError('gold record heading range is invalid')
    preceding_ids = [line for line in lines[:start] if re.match(r'\s*entry_id:', line)]
    if not preceding_ids or row['entry_id'] != preceding_ids[-1].split(':', 1)[1].strip().strip('\"\''):
        raise ValueError('gold record identity does not match frozen coordinates')
    heading = re.sub(r'^#+\s*', '', lines[start - 1])
    if heading != record['title'] and not record['title'].endswith(' - ' + heading):
        raise ValueError('gold record heading does not match frozen coordinates')
    return _record_text(repo, row)


def run(repo: Path, codex_home: Path, output: Path):
    manifest = build_manifest(repo)
    original, original_sha = baseline_parser(repo)
    revised = DecisionParser()
    if original.backend != revised.backend or revised.backend == 'rules':
        raise RuntimeError('Both benchmark arms must use the same pinned spaCy pipeline')
    # Refuse silently changed production rules; this experiment never tunes them.
    for relative in ['hosted/capture/parser.py', 'hosted/capture/incremental.py']:
        pinned = subprocess.check_output(['git', 'show', f'{REVISED}:{relative}'], cwd=repo)
        if pinned.replace(b'\r\n', b'\n') != (repo / relative).read_bytes().replace(b'\r\n', b'\n'):
            raise RuntimeError(f'frozen parser drift: {relative}')
    rules_cache = {}
    actual_rules = revised._linguistic_rules

    def cached_rules(text):
        if text not in rules_cache:
            rules_cache[text] = actual_rules(text)
        return rules_cache[text]

    original._linguistic_rules = revised._linguistic_rules = cached_rules
    align = _load_alignment_parser(repo)
    paths = _rollout_paths(codex_home)
    metas = {r: meta for r, path in paths.items() if (meta := align.read_session_meta(path)) is not None}
    rows = [r for r in manifest['rows'] if r['split'] != 'audit_only'
            and r['record_kind'] == 'Decision' and r['adjudication_label'] == 'verified_source'
            and r['evidence_coordinates']]
    needed = {str(ref['rollout_id']).lower() for row in rows for ref in row['evidence_coordinates']}
    task_ids = {metas[r].session_id for r in needed if r in metas}
    for _ in range(8):
        task_ids.update(m.parent_thread_id for m in metas.values() if m.session_id in task_ids and m.parent_thread_id)
    needed.update(r for r, m in metas.items() if m.session_id in task_ids)
    messages_by_rollout, input_hashes = {}, {}
    for rollout in sorted(needed):
        if rollout not in metas:
            continue
        path = paths[rollout]
        before = sha(path.read_bytes())
        blocks = align.parse_rollout(path, metas[rollout])
        if before != sha(path.read_bytes()):
            raise RuntimeError('A source changed during replay loading')
        input_hashes[rollout] = before
        messages_by_rollout[rollout] = [dict(rollout_id=rollout, turn=block.turn_number,
            source_ordinal=item.source_ordinal, actor='agent' if item.role == 'assistant' else 'user',
            timestamp=item.timestamp, text=item.text) for block in blocks for item in block.items
            if item.role in {'user', 'assistant'} and item.source_ordinal is not None]
    lookup = {coordinate(m): m for messages in messages_by_rollout.values() for m in messages}
    results = []
    for index, row in enumerate(rows):
        refs = row['evidence_coordinates']
        cited = [lookup[coordinate(ref)] for ref in refs if coordinate(ref) in lookup]
        base = {'case_id': row['case_id'], 'split': row['split'], 'total_gold_refs': len(refs),
                'accessible_visible_refs': len(cited)}
        if not cited:
            results.append({**base, 'status': 'no_accessible_visible_anchor'})
            continue
        anchor = max(cited, key=incremental.order)
        rollout = anchor['rollout_id']
        current = causal_prefix(messages_by_rollout[rollout], anchor)
        # Select parent context from actual lineage, not gold text or gold's cited parent list.
        parent_tasks = set()
        parent_task = metas[rollout].parent_thread_id
        for _ in range(8):
            if not parent_task or parent_task in parent_tasks:
                break
            parent_tasks.add(parent_task)
            parent_meta = next((m for m in metas.values() if m.session_id == parent_task), None)
            parent_task = parent_meta.parent_thread_id if parent_meta else None
        parents = [m for r, messages in messages_by_rollout.items()
                   if metas[r].session_id in parent_tasks for m in messages
                   if incremental.utc_time(m) and incremental.utc_time(anchor)
                   and incremental.utc_time(m) <= incremental.utc_time(anchor)]
        # Bound parent evidence to the latest twenty distinct lineage turns.
        parent_turns = list(dict.fromkeys((m['rollout_id'], m['turn'])
                           for m in sorted(parents, key=incremental.order)))[-20:]
        parents = [m for m in parents if (m['rollout_id'], m['turn']) in parent_turns]
        marker = cue_marker(anchor, oracle=True)
        legacy = original.parse(rollout, current, marker=marker)
        newer, cached_cost, newer_window = replay_revised(revised, rollout, current, marker, parents)
        uncached, repeated_cost, _ = replay_revised(revised, rollout, current, marker, parents, recompute=True)
        identical = normalize_ablation(newer) == normalize_ablation(uncached)
        if not identical:
            raise RuntimeError(f'Unexplained delta ablation mismatch in {row["case_id"]}')
        legacy_window = original.region(rollout, current, marker_turn=marker['turn'])['messages']
        # Gold contents are first opened AFTER both arms and the ablation are frozen.
        gold_text = validated_gold_text(repo, row)
        review_drafts = {}
        for name, drafts in [('legacy', legacy), ('revised', newer)]:
            compact = []
            seen = set()
            for draft in drafts:
                fields = {key: draft.get(key) for key in ['issue', 'scope', 'proposal', 'selected_action',
                          'agreement_quote', 'reason', 'conditions', 'state', 'deciding_actor']}
                signature = encoded(fields)
                if signature not in seen:
                    compact.append(fields)
                    seen.add(signature)
            review_drafts[name] = compact
        # Arm aliases vary by case; mapping remains outside the review packet.
        reverse = int(sha(row['case_id'].encode())[-1], 16) % 2 == 1
        arms = ['revised', 'legacy'] if reverse else ['legacy', 'revised']
        results.append({**base, 'status': 'replayed', 'anchor': {k: anchor[k] for k in ['rollout_id','turn','source_ordinal']},
            'cue_at_anchor': cue_marker(anchor) is not None,
            'cue_at_any_cited_event': any(cue_marker(m) for m in cited),
            'legacy': {'drafts': len(legacy), 'accepted': sum(d['state'] == 'accepted' for d in legacy),
                       'all_visible_refs_in_window': coverage(cited, legacy_window),
                       'all_cited_refs_in_window': coverage(refs, legacy_window)},
            'revised': {'drafts': len(newer), 'accepted': sum(d['state'] == 'accepted' for d in newer),
                        'complete': sum(bool(d.get('complete')) for d in newer),
                        'all_visible_refs_in_window': coverage(cited, newer_window),
                        'all_cited_refs_in_window': coverage(refs, newer_window)},
            'ablation': {'identical_outputs': identical, 'delta': cached_cost, 'reparse': repeated_cost},
            'arm_mapping': dict(zip(['A','B'], arms)),
            'review': {'case_id': row['case_id'], 'gold_record': gold_text,
                       'source_evidence': cited, 'A': review_drafts[arms[0]], 'B': review_drafts[arms[1]]},
        })
        if (index + 1) % 10 == 0:
            print(f'Replayed {index + 1}/{len(rows)} cases', flush=True)
    summary = {'schema': 'p02-paired-oracle-replay-v1', 'baseline_commit': BASELINE,
               'revised_commit': REVISED, 'baseline_parser_sha256': original_sha,
               'manifest_sha256': manifest['manifest_sha256'], 'backend': revised.backend,
               'protocol_sha256': sha((repo / 'hosted/evaluation/PAIRED-REPLAY-PLAN.md').read_bytes()),
               'source_hashes': input_hashes, 'eligible': len(rows),
               'status_counts': dict(Counter(r['status'] for r in results)),
               'splits': dict(Counter(r['split'] for r in results)),
               'semantic_review_status': 'pending', 'autonomous_detection_recall': None,
               'cases': [public_case(r) for r in results],
               'limitations': ['oracle source anchors, not autonomous marker detection',
                               'last cited visible event; no future messages supplied',
                               'positive, decision-known corpus; no population precision',
                               'new retrieval/rules differ; caching effect isolated only by ablation']}
    private = Path(tempfile.mkdtemp(prefix='p02-paired-owner-'))
    for row in results:
        if 'review' in row:
            (private / (row['case_id'].replace(':','_') + '.json')).write_text(encoded(row['review']), encoding='utf-8')
    (private / 'raw-results.json').write_text(encoded(results), encoding='utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(encoded({'report': str(output), 'private_review_directory': str(private),
                   'eligible': len(rows), 'status_counts': summary['status_counts']}), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--codex-home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.repo.resolve(), args.codex_home.resolve(), args.output.resolve())
