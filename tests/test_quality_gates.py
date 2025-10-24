"""Test graduated quality gates."""
from lily_books.chains.checker import evaluate_chapter_quality
from lily_books.models import ParaPair, QAIssue, QAReport


def test_critical_issue_fails():
    """Test that LLM-flagged critical issues cause failure."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original text",
            modern="Modern text",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                issues=[
                    QAIssue(
                        type="content",
                        description="Critical problem",
                        severity="critical",
                    )
                ],
            ),
        )
    ]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert not passed
    assert "critical issues" in reason.lower()
    assert len(issues) == 1


def test_low_fidelity_fails():
    """Test that fidelity below threshold causes failure."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(fidelity_score=80, readability_grade=8.0, issues=[]),
        )
    ]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert not passed
    assert "fidelity too low" in reason.lower()


def test_readability_out_of_range_fails():
    """Test that readability outside range causes failure."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(fidelity_score=95, readability_grade=15.0, issues=[]),
        )
    ]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert not passed
    assert "too complex" in reason.lower()


def test_readability_too_simple_fails():
    """Test that readability below minimum causes failure."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(fidelity_score=95, readability_grade=3.0, issues=[]),
        )
    ]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert not passed
    assert "oversimplified" in reason.lower()


def test_high_severity_issues_pass_with_warning():
    """Test that high severity issues log warnings but don't fail."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                issues=[
                    QAIssue(type="style", description="Minor issue", severity="high")
                ],
            ),
        )
    ]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert passed  # High severity doesn't fail
    assert len(issues) == 1  # But issue is tracked


def test_quote_preservation_critical_fails():
    """Test that quote preservation failures cause failure when configured as critical."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                quote_count_match=False,
                issues=[],
            ),
        )
    ]

    quality_settings = {
        "min_fidelity": 85,
        "readability_range": (5.0, 12.0),
        "quote_severity": "critical",
    }
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert not passed
    assert "quote preservation failed" in reason.lower()


def test_quote_preservation_high_passes():
    """Test that quote preservation failures pass when configured as high severity."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                quote_count_match=False,
                issues=[],
            ),
        )
    ]

    quality_settings = {
        "min_fidelity": 85,
        "readability_range": (5.0, 12.0),
        "quote_severity": "high",
    }
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert passed  # High severity doesn't fail
    assert len(issues) == 1  # But issue is tracked


def test_emphasis_preservation_critical_fails():
    """Test that emphasis preservation failures cause failure when configured as critical."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                emphasis_preserved=False,
                issues=[],
            ),
        )
    ]

    quality_settings = {
        "min_fidelity": 85,
        "readability_range": (5.0, 12.0),
        "emphasis_severity": "critical",
    }
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert not passed
    assert "emphasis preservation failed" in reason.lower()


def test_emphasis_preservation_high_passes():
    """Test that emphasis preservation failures pass when configured as high severity."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                emphasis_preserved=False,
                issues=[],
            ),
        )
    ]

    quality_settings = {
        "min_fidelity": 85,
        "readability_range": (5.0, 12.0),
        "emphasis_severity": "high",
    }
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert passed  # High severity doesn't fail
    assert len(issues) == 1  # But issue is tracked


def test_perfect_chapter_passes():
    """Test that a perfect chapter passes all quality gates."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                quote_count_match=True,
                emphasis_preserved=True,
                issues=[],
            ),
        )
    ]

    quality_settings = {
        "min_fidelity": 85,
        "readability_range": (5.0, 12.0),
        "quote_severity": "high",
        "emphasis_severity": "high",
    }
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert passed
    assert reason == ""
    assert len(issues) == 0


def test_multiple_paragraphs_min_fidelity():
    """Test that minimum fidelity is calculated across all paragraphs."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(fidelity_score=90, readability_grade=8.0, issues=[]),
        ),
        ParaPair(
            i=1,
            para_id="p1",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=80, readability_grade=8.0, issues=[]
            ),  # This should fail
        ),
        ParaPair(
            i=2,
            para_id="p2",
            orig="Original",
            modern="Modern",
            qa=QAReport(fidelity_score=95, readability_grade=8.0, issues=[]),
        ),
    ]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert not passed
    assert "fidelity too low" in reason.lower()
    assert "min=80" in reason


def test_multiple_paragraphs_readability():
    """Test that readability is checked for all paragraphs."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(fidelity_score=95, readability_grade=8.0, issues=[]),
        ),
        ParaPair(
            i=1,
            para_id="p1",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=95, readability_grade=15.0, issues=[]
            ),  # This should fail
        ),
        ParaPair(
            i=2,
            para_id="p2",
            orig="Original",
            modern="Modern",
            qa=QAReport(fidelity_score=95, readability_grade=9.0, issues=[]),
        ),
    ]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert not passed
    assert "too complex" in reason.lower()
    assert "Paragraph 1" in reason


def test_no_qa_data_passes():
    """Test that chapters with no QA data pass (edge case)."""
    pairs = [ParaPair(i=0, para_id="p0", orig="Original", modern="Modern", qa=None)]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert passed  # No QA data means no quality gates to fail
    assert reason == ""
    assert len(issues) == 0


def test_mixed_severity_issues():
    """Test handling of mixed severity issues."""
    pairs = [
        ParaPair(
            i=0,
            para_id="p0",
            orig="Original",
            modern="Modern",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                issues=[
                    QAIssue(
                        type="style", description="High severity issue", severity="high"
                    ),
                    QAIssue(
                        type="minor", description="Low severity issue", severity="low"
                    ),
                ],
            ),
        )
    ]

    quality_settings = {"min_fidelity": 85, "readability_range": (5.0, 12.0)}
    passed, reason, issues = evaluate_chapter_quality(pairs, [], quality_settings)

    assert passed  # No critical issues
    assert len(issues) == 2  # Both issues tracked
