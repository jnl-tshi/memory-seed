import json
from unittest.mock import patch

import pytest

from hosted.capture.incremental import ExtractionState
from hosted.capture.parser import DecisionParser


def message(turn, actor, text, **extra):
    return dict(turn=turn, source_ordinal=turn * 10, actor=actor, text=text, **extra)


def marker(turn=2, quote="Yes, that's the right approach.", **extra):
    return dict(turn=turn, source_ordinal=turn * 10, trigger_quote=quote,
                issue_hint='not authoritative', state='accepted', **extra)


def test_delta_processing_is_observed_not_just_counted():
    parser = DecisionParser()
    messages = [message(1, 'agent', 'Issue: durable capture. I propose we use SQLite for the capture queue.'),
                message(2, 'user', "Yes, that's the right approach."),
                message(3, 'agent', 'Use another database for a different project.')]
    with patch.object(parser, 'extract_component', wraps=parser.extract_component) as extract:
        drafts = parser.parse_stepped('r', messages, marker=marker())
    assert len(drafts) == 1 and drafts[0]['complete']
    assert [call.args[0]['source_ordinal'] for call in extract.call_args_list] == [20, 10]
    assert drafts[0]['selected_action'] == 'use SQLite for the capture queue'
    trace = drafts[0]['source']['retrieval_trace']
    assert trace['total_messages_processed'] == 2
    assert trace['selected_stage'] == 'backward_1'


def test_forward_delta_can_supply_later_grounded_acceptance():
    parser = DecisionParser()
    messages = [message(2, 'agent', 'Issue: durable capture. I propose we use SQLite for the capture queue.'),
                message(3, 'user', 'Yes, agreed.'),
                message(4, 'user', 'Use PostgreSQL for a different project.')]
    mark = marker(quote=messages[0]['text'])
    with patch.object(parser, 'extract_component', wraps=parser.extract_component) as extract:
        drafts = parser.parse_stepped('r', messages, marker=mark)
    assert drafts[0]['complete']
    assert len(extract.call_args_list) == 2
    assert drafts[0]['source']['retrieval_trace']['selected_stage'] == 'forward_1'


@pytest.mark.parametrize('boundary', ['implementation_started', 'decision_marker', 'task_boundary'])
def test_boundary_does_not_fold_later_agreement_into_old_decision(boundary):
    parser = DecisionParser()
    messages = [message(2, 'agent', 'I propose we use SQLite for the capture queue.'),
                message(3, 'agent', 'A boundary occurred.', **{boundary: True}),
                message(4, 'user', 'Yes, agreed.')]
    drafts = parser.parse_stepped('r', messages, marker=marker(quote=messages[0]['text']))
    assert drafts[0]['state'] == 'proposed'
    assert drafts[0]['source']['retrieval_trace']['stop_reason'] == 'lifecycle_boundary_requires_new_decision'


@pytest.mark.parametrize('text', ['Use that approach for capture.', 'Use structured markers.'])
def test_unresolved_reference_or_missing_scope_cannot_close(text):
    drafts = DecisionParser().parse_stepped('r', [message(2, 'user', text)], marker=marker(quote=text))
    assert drafts and not drafts[0]['complete']
    assert drafts[0]['missing_components']


def test_replayed_coordinate_does_not_repeat_extraction_and_changed_content_fails():
    parser = DecisionParser()
    state = ExtractionState(parser, 'r')
    item = message(1, 'user', 'Use SQLite for the queue.')
    with patch.object(parser, 'extract_component', wraps=parser.extract_component) as extract:
        state.feed([item])
        state.feed([item])
    assert extract.call_count == 1
    with pytest.raises(ValueError, match='changed content'):
        state.feed([{**item, 'text': 'Use another option.'}])


def test_untrusted_marker_quote_and_agent_agreement_do_not_authorize():
    messages = [message(1, 'agent', 'I propose we use SQLite for capture.'),
                message(2, 'agent', 'Yes, agreed.')]
    parser = DecisionParser()
    assert not any(c['state'] == 'accepted' for c in parser.parse('r', messages))
    assert parser.parse_stepped('r', messages, marker=marker(quote='not present')) == []


def test_three_runs_are_byte_identical_with_same_inputs():
    parser = DecisionParser()
    messages = [message(2, 'user', 'Use SQLite for the queue because it survives restart.')]
    runs = [json.dumps(parser.parse_stepped('r', messages, marker=marker(quote=messages[0]['text'])),
                       sort_keys=True) for _ in range(3)]
    assert len(set(runs)) == 1


def test_offsets_cannot_reverse_authoritative_rollout_order():
    messages = [message(1, 'user', 'Yes.', timestamp='2026-01-01T10:00:00+02:00'),
                message(2, 'agent', 'Issue: storage. Use SQLite in the queue.', timestamp='2026-01-01T09:00:00Z')]
    drafts = DecisionParser().parse_stepped('r', messages, marker=marker(quote=messages[1]['text']))
    assert all(c['state'] != 'accepted' for c in drafts)


def test_acknowledgement_after_unrelated_question_is_not_grounded():
    messages = [message(1, 'agent', 'Issue: storage. Use SQLite in the queue.'),
                message(2, 'agent', 'Should I delete the backups?'),
                message(3, 'user', 'Yes.')]
    assert all(c['state'] != 'accepted' for c in DecisionParser().parse('r', messages))


def test_batch_parse_retains_system_boundary_sentinels():
    messages = [message(1, 'agent', 'Issue: storage. Use SQLite in the queue.'),
                message(2, 'system', 'Implementation started.', implementation_started=True),
                message(3, 'user', 'Yes.')]
    assert all(c['state'] != 'accepted' for c in DecisionParser().parse('r', messages))


def test_scope_is_not_fabricated_into_issue():
    text = 'Use SQLite in the queue.'
    drafts = DecisionParser().parse_stepped('r', [message(2, 'user', text)], marker=marker(quote=text))
    assert drafts[0]['issue'] is None
    assert 'issue' in drafts[0]['missing_components']


def test_evaluation_does_not_overwrite_frozen_results(tmp_path):
    from hosted.capture.evaluation import run_evaluation
    with pytest.raises(ValueError, match='frozen baseline'):
        run_evaluation(tmp_path, tmp_path, tmp_path / 'hosted' / 'evaluation' / 'results')
