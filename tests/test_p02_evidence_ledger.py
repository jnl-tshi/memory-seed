"""Adversarial checks for cited, same-rollout decision evidence."""

import pytest

from hosted.capture.evidence_ledger import EvidenceLedger


def message(turn, ordinal, actor, text):
    return {"rollout_id": "r", "turn": turn, "source_ordinal": ordinal,
            "actor": actor, "text": text}


def cite(source, quote):
    start = source["text"].index(quote)
    return {"rollout_id": source["rollout_id"], "turn": source["turn"],
            "source_ordinal": source["source_ordinal"], "start": start,
            "end": start + len(quote), "quote": quote}


def answer(value, *citations):
    return {"value": value, "citations": list(citations)}


def questions(**overrides):
    result = {slot: None for slot in EvidenceLedger.SLOTS}
    result.update(overrides)
    return result


def direct_answers(source):
    whole = cite(source, source["text"])
    return questions(issue=answer("capture", whole),
                     selected_action=answer("Use capture", whole),
                     deciding_actor=answer("user", whole),
                     acceptance=answer("directive", whole),
                     scope=answer("this project", whole),
                     proposal_reference=answer("direct directive", whole),
                     topic_origin=answer("direct directive", whole))


def test_direct_user_direction_established_without_reason():
    source = message(2, 4, "user", "Use capture for this project.")
    ledger = EvidenceLedger(("r", 2, 4))
    ledger.add_disclosure_batch([source])
    result = ledger.ingest_candidate("direct", direct_answers(source))
    assert result["decision_established"] is True
    assert result["all_questions_answered"] is False
    assert result["explanation_complete"] is False
    assert result["semantic_verified"] is False
    assert result["authoritative"] is False
    assert result["curator_review_required"] is True
    assert result["answers"]["reason"] is None
    assert result["source_messages"] == [source]
    assert ledger.assess("direct", source_window_exhausted=True)["missing_slots"] == ["conditions", "reason"]


def test_two_message_proposal_and_amendment_exclusion():
    first = message(0, 0, "assistant", "Plan A: capture the decision.")
    second = message(0, 1, "assistant", "Plan A: exclude private files.")
    approval = message(1, 2, "user", "Yes, use that plan, but exclude archived files.")
    ledger = EvidenceLedger(("r", 1, 2))
    ledger.add_disclosure_batch([approval])
    ledger.add_disclosure_batch([first, second])
    answers = questions(
        issue=answer("decision capture", cite(first, "capture the decision")),
        selected_action=answer("Plan A", cite(first, "Plan A"), cite(second, "Plan A")),
        deciding_actor=answer("user", cite(approval, "Yes")),
        acceptance=answer("Yes, use that plan", cite(approval, "Yes, use that plan")),
        scope=answer("exclude private and archived files", cite(second, "exclude private files"), cite(approval, "exclude archived files")),
        conditions=answer("exclude archived files", cite(approval, "exclude archived files")),
        proposal_reference=answer("that plan", cite(approval, "that plan")),
        topic_origin=answer("Plan A", cite(first, "Plan A")),
        reason=answer("privacy", cite(second, "private files")),
    )
    link = {"mention": cite(approval, "that plan"),
            "antecedents": [cite(first, "Plan A"), cite(second, "Plan A")],
            "status": "resolved"}
    result = ledger.ingest_candidate("amended", answers, [link])
    assert result["decision_established"] is True
    assert result["all_questions_answered"] is True
    assert result["explanation_complete"] is True
    assert len(result["reference_links"][0]["antecedents"]) == 2


def test_ambiguous_that_remains_unresolved():
    first = message(0, 0, "assistant", "Use option A.")
    second = message(0, 1, "assistant", "Use option B.")
    approval = message(1, 2, "user", "Yes, do that.")
    ledger = EvidenceLedger(("r", 1, 2))
    ledger.add_disclosure_batch([first, second, approval])
    answers = questions(selected_action=answer("an option", cite(first, "option A")),
                        deciding_actor=answer("user", cite(approval, "Yes")),
                        acceptance=answer("Yes", cite(approval, "Yes")),
                        scope=answer("option", cite(first, "option A")),
                        proposal_reference=answer("that", cite(approval, "that")))
    link = {"mention": cite(approval, "that"),
            "antecedents": [cite(first, "option A"), cite(second, "option B")],
            "status": "ambiguous"}
    result = ledger.ingest_candidate("ambiguous", answers, [link])
    assert result["decision_established"] is False
    assert result["unresolved_references"] == [link]


def test_cross_message_proposal_reference_needs_link_covering_action_sources():
    first = message(0, 0, "assistant", "Plan A: capture decisions.")
    second = message(0, 1, "assistant", "Plan A: exclude private files.")
    approval = message(1, 2, "user", "Yes, that plan.")
    ledger = EvidenceLedger(("r", 1, 2))
    ledger.add_disclosure_batch([first, second, approval])
    answers = questions(
        selected_action=answer("Plan A", cite(first, "Plan A"), cite(second, "Plan A")),
        deciding_actor=answer("user", cite(approval, "Yes")),
        acceptance=answer("Yes", cite(approval, "Yes")),
        scope=answer("exclude private files", cite(second, "exclude private files")),
        proposal_reference=answer("that plan", cite(approval, "that plan")))
    absent = ledger.ingest_candidate("absent-link", answers)
    assert absent["decision_established"] is False
    assert absent["unresolved_references"][0]["status"] == "unresolved"
    partial = {"mention": cite(approval, "that plan"),
               "antecedents": [cite(first, "Plan A")], "status": "resolved"}
    partial_result = ledger.ingest_candidate("partial-link", answers, [partial])
    assert partial_result["decision_established"] is False
    full = {"mention": cite(approval, "that plan"),
            "antecedents": [cite(first, "Plan A"), cite(second, "Plan A")],
            "status": "resolved"}
    assert ledger.ingest_candidate("full-link", answers, [full])["decision_established"] is True


def test_wrong_actor_and_reverse_acceptance_chronology_rejected():
    approval = message(0, 0, "user", "Yes.")
    proposal = message(1, 1, "assistant", "Use option A.")
    ledger = EvidenceLedger(("r", 1, 1))
    ledger.add_disclosure_batch([approval, proposal])
    base = questions(selected_action=answer("A", cite(proposal, "option A")),
                     deciding_actor=answer("user", cite(approval, "Yes")),
                     acceptance=answer("Yes", cite(approval, "Yes")))
    with pytest.raises(ValueError, match="chronology"):
        ledger.ingest_candidate("reverse", base)
    wrong = dict(base, acceptance=answer("accepted", cite(proposal, "Use option A")))
    with pytest.raises(ValueError, match="user-authored"):
        ledger.ingest_candidate("wrong", wrong)
    assert ledger.candidates == {}


def test_topic_origin_current_turn_requires_citation():
    source = message(2, 4, "user", "Use capture for this project.")
    ledger = EvidenceLedger(("r", 2, 4))
    ledger.add_disclosure_batch([source])
    answers = direct_answers(source)
    answers["topic_origin"] = None
    result = ledger.ingest_candidate("missing-origin", answers)
    assert result["decision_established"] is True
    assert result["all_questions_answered"] is False
    with pytest.raises(ValueError, match="citation"):
        ledger.ingest_candidate("uncited-origin", dict(answers, topic_origin={"value": "current turn", "citations": []}))


def test_exact_quote_unknown_source_and_later_source_refused():
    source = message(2, 4, "user", "Use capture for this project.")
    later = message(2, 5, "assistant", "Done.")
    ledger = EvidenceLedger(("r", 2, 4))
    with pytest.raises(ValueError, match="later"):
        ledger.add_disclosure_batch([source, later])
    assert ledger.source_messages == []
    ledger.add_disclosure_batch([source])
    bad_quote = cite(source, "Use capture") | {"quote": "use capture"}
    with pytest.raises(ValueError, match="quote"):
        ledger.ingest_candidate("bad", questions(issue=answer("capture", bad_quote)))
    unknown = cite(source, "Use capture") | {"source_ordinal": 3}
    with pytest.raises(ValueError, match="unknown citation source"):
        ledger.ingest_candidate("unknown", questions(issue=answer("capture", unknown)))
    assert ledger.candidates == {}


def test_malformed_link_rolls_back_candidate_and_disclosure_is_idempotent():
    source = message(2, 4, "user", "Use capture for this project.")
    ledger = EvidenceLedger(("r", 2, 4))
    ledger.add_disclosure_batch([source])
    ledger.add_disclosure_batch([source])
    assert ledger.source_messages == [source]
    malformed = {"mention": cite(source, "Use capture"), "antecedents": [], "status": "resolved"}
    with pytest.raises(ValueError, match="antecedent"):
        ledger.ingest_candidate("direct", direct_answers(source), [malformed])
    assert ledger.candidates == {}
    changed = dict(source, text="Use something else.")
    with pytest.raises(ValueError, match="changed content"):
        ledger.add_disclosure_batch([changed])
    assert ledger.source_messages == [source]


def test_reference_antecedent_must_precede_mention():
    first = message(0, 0, "assistant", "Option A.")
    later = message(1, 1, "user", "That is fine.")
    ledger = EvidenceLedger(("r", 1, 1))
    ledger.add_disclosure_batch([first, later])
    backwards = {"mention": cite(first, "Option A"),
                 "antecedents": [cite(later, "That")], "status": "resolved"}
    with pytest.raises(ValueError, match="precede"):
        ledger.ingest_candidate("backwards", questions(), [backwards])


def test_same_candidate_revises_atomically_after_disclosure():
    proposal = message(0, 0, "assistant", "Plan A uses SQLite.")
    approval = message(1, 1, "user", "Yes, use that plan for this project.")
    ledger = EvidenceLedger(("r", 1, 1))
    ledger.add_disclosure_batch([approval])
    early = questions(deciding_actor=answer("user", cite(approval, "Yes")),
                      acceptance=answer("Yes", cite(approval, "Yes")),
                      proposal_reference=answer("that plan", cite(approval, "that plan")))
    initial = ledger.ingest_candidate("c", early)
    assert initial["decision_established"] is False
    ledger.add_disclosure_batch([proposal])
    revised = dict(early,
                   selected_action=answer("SQLite", cite(proposal, "SQLite")),
                   scope=answer("this project", cite(approval, "this project")),
                   reason=answer("uses SQLite", cite(proposal, "uses SQLite")))
    ambiguous = {"mention": cite(approval, "that plan"),
                 "antecedents": [cite(proposal, "Plan A")], "status": "ambiguous"}
    assert ledger.ingest_candidate("c", revised, [ambiguous])["decision_established"] is False
    resolved = dict(ambiguous, status="resolved")
    updated = ledger.ingest_candidate("c", revised, [resolved])
    assert updated["decision_established"] is True
    assert updated["explanation_complete"] is True
    assert updated["semantic_verified"] is False
    assert updated["authoritative"] is False
    assert initial["answers"] == early
    malformed = dict(resolved, antecedents=[cite(proposal, "Plan A") | {"quote": "plan A"}])
    with pytest.raises(ValueError, match="quote"):
        ledger.ingest_candidate("c", revised, [malformed])
    assert ledger.candidates["c"]["reference_links"] == [resolved]
    updated["answers"]["reason"]["value"] = "changed"
    assert ledger.candidates["c"]["answers"]["reason"]["value"] == "uses SQLite"


def test_same_user_directive_acceptance_before_action_is_valid():
    directive = message(1, 1, "user", "Yes, use SQLite for this project.")
    ledger = EvidenceLedger(("r", 1, 1))
    ledger.add_disclosure_batch([directive])
    answers = questions(
        selected_action=answer("SQLite", cite(directive, "SQLite")),
        deciding_actor=answer("user", cite(directive, "Yes")),
        acceptance=answer("Yes", cite(directive, "Yes")),
        scope=answer("this project", cite(directive, "this project")),
        proposal_reference=answer("direct directive", cite(directive, "use SQLite")))
    assert ledger.ingest_candidate("directive", answers)["decision_established"] is True
    earlier = message(0, 0, "user", "Yes.")
    ledger.add_disclosure_batch([earlier])
    backwards = dict(answers, acceptance=answer("Yes", cite(earlier, "Yes")))
    with pytest.raises(ValueError, match="chronology"):
        ledger.ingest_candidate("directive", backwards)
    assert ledger.candidates["directive"]["answers"]["acceptance"]["citations"] == [cite(directive, "Yes")]


def test_same_message_antecedent_before_mention_is_valid_but_overlap_is_not():
    source = message(1, 1, "user", "Plan A uses SQLite. I accept that plan.")
    ledger = EvidenceLedger(("r", 1, 1))
    ledger.add_disclosure_batch([source])
    mention = cite(source, "that plan")
    preceding = {"mention": mention,
                 "antecedents": [cite(source, "Plan A uses SQLite")],
                 "status": "resolved"}
    assert ledger.ingest_candidate("same-message", questions(), [preceding])["reference_links"] == [preceding]
    adjacent = dict(preceding, antecedents=[cite(source, "accept ")])
    assert ledger.ingest_candidate("same-message", questions(), [adjacent])["reference_links"] == [adjacent]
    overlap = dict(preceding, antecedents=[cite(source, "accept that")])
    with pytest.raises(ValueError, match="precede"):
        ledger.ingest_candidate("same-message", questions(), [overlap])
    later = dict(preceding, mention=cite(source, "Plan A"),
                 antecedents=[cite(source, "that plan")])
    with pytest.raises(ValueError, match="precede"):
        ledger.ingest_candidate("same-message", questions(), [later])
