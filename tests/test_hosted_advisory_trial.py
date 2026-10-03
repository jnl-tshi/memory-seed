from hosted.evaluation.advisory_trial import run_trial


def test_synthetic_advisory_trial_counts_and_limit():
    result = run_trial()
    metrics = result["metrics"]
    assert metrics["cases"] == 9
    assert metrics["useful_suggestions"] == 5
    assert metrics["false_suggestions"] == 1
    assert metrics["missed_suggestions"] == 0
    assert metrics["unresolved_cases"] == 1
    assert metrics["invalid_citations_accepted"] == 0
    assert metrics["invalid_citations_rejected"] == 1
    assert metrics["records_only_cases"] == 6
    assert metrics["source_check_cases"] == 2
    assert metrics["model_tokens"] == {"prompt_tokens": 0, "completion_tokens": 0}
