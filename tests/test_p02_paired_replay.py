from hosted.evaluation.paired_replay import causal_prefix, coverage, cue_marker
from hosted.evaluation.paired_replay import replay_revised, normalize_ablation
from hosted.capture.parser import DecisionParser
from hosted.evaluation.paired_replay import validated_gold_text, public_case
import pytest


def test_prefix_cannot_read_future_in_same_turn():
    rows = [dict(rollout_id='r', turn=1, source_ordinal=i, actor='user', text='Use A.') for i in (1, 2, 3)]
    assert [r['source_ordinal'] for r in causal_prefix(rows, rows[1])] == [1, 2]


def test_coverage_requires_exact_coordinate_not_just_turn():
    refs = [dict(rollout_id='r', turn=1, source_ordinal=2)]
    assert not coverage(refs, [dict(rollout_id='r', turn=1, source_ordinal=1)])
    assert coverage(refs, refs)


def test_cue_uses_only_observed_message_and_does_not_supply_gold_issue():
    row = dict(rollout_id='r', turn=1, source_ordinal=3, actor='user', text='Yes, use SQLite for the queue.')
    mark = cue_marker(row)
    assert mark['source_ordinal'] == 3
    assert mark['trigger_quote'] in row['text']
    assert mark['issue_hint'] == 'observed decision signal'
    assert cue_marker({**row, 'text': 'Perhaps tomorrow.'}) is None


def test_ablation_preserves_meaning_and_counts_repeated_work():
    messages = [dict(rollout_id='r', turn=t, source_ordinal=t, actor=a, text=text) for t, a, text in [
        (1, 'agent', 'Issue: durable storage. I propose we use SQLite for the queue.'),
        (3, 'agent', 'Some background context.'),
        (4, 'user', 'Yes, agreed.')]]
    parser = DecisionParser()
    mark = cue_marker(messages[-1], oracle=True)
    delta, delta_cost, _ = replay_revised(parser, 'r', messages, mark, [], recompute=False)
    repeated, repeated_cost, _ = replay_revised(parser, 'r', messages, mark, [], recompute=True)
    assert delta and delta[0]['complete']
    assert normalize_ablation(delta) == normalize_ablation(repeated)
    assert delta_cost['extraction_calls'] == 3
    assert repeated_cost['extraction_calls'] == 6


def test_gold_slice_requires_matching_entry_and_heading(tmp_path):
    path = tmp_path / 'record.md'
    path.write_text('entry_id: sample\n#### D1 - Choice\n- D: Use A.\n', encoding='utf-8')
    row = {'case_id': 'sample:d1', 'entry_id': 'sample',
           'record': {'path': 'record.md', 'start_line': 2, 'end_line': 3, 'title': 'D1 - Choice'}}
    assert validated_gold_text(tmp_path, row).startswith('#### D1 - Choice')
    with pytest.raises(ValueError, match='gold record identity'):
        validated_gold_text(tmp_path, {**row, 'entry_id': 'another'})
    with pytest.raises(ValueError, match='gold record heading'):
        validated_gold_text(tmp_path, {**row, 'record': {**row['record'], 'start_line': 3}})


def test_public_case_excludes_private_evidence():
    assert public_case({'case_id': 'x', 'review': {'private': 'source'}, 'raw_drafts': ['raw']}) == {'case_id': 'x'}
