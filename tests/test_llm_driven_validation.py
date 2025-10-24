"""Tests for LLM-driven validation approach."""

from lily_books.models import (
    CheckerOutput,
    ModernizedParagraph,
    QAIssue,
    QAReport,
    WriterOutput,
)
from lily_books.utils.validators import (
    log_llm_decision,
    safe_parse_checker_output,
    safe_parse_writer_output,
    sanity_check_checker_output,
    sanity_check_writer_output,
)


def test_safe_parse_writer_output():
    """Test safe parsing of WriterOutput."""
    # Test with valid WriterOutput
    valid_output = WriterOutput(
        paragraphs=[ModernizedParagraph(modern="Test paragraph")]
    )

    result = safe_parse_writer_output(valid_output)
    assert result is not None
    assert len(result.paragraphs) == 1
    assert result.paragraphs[0].modern == "Test paragraph"

    # Test with dict input
    dict_output = {"paragraphs": [{"modern": "Test paragraph"}]}

    result = safe_parse_writer_output(dict_output)
    assert result is not None
    assert len(result.paragraphs) == 1
    assert result.paragraphs[0].modern == "Test paragraph"

    # Test with invalid input
    result = safe_parse_writer_output("invalid")
    assert result is None


def test_safe_parse_checker_output():
    """Test safe parsing of CheckerOutput."""
    # Test with valid CheckerOutput
    valid_output = CheckerOutput(
        fidelity_score=85, confidence=0.8, llm_reasoning="Good modernization"
    )

    result = safe_parse_checker_output(valid_output)
    assert result is not None
    assert result.fidelity_score == 85
    assert result.confidence == 0.8
    assert result.llm_reasoning == "Good modernization"

    # Test with dict input
    dict_output = {
        "fidelity_score": 90,
        "confidence": 0.9,
        "llm_reasoning": "Excellent modernization",
        "metadata": {"model": "claude-sonnet"},
    }

    result = safe_parse_checker_output(dict_output)
    assert result is not None
    assert result.fidelity_score == 90
    assert result.confidence == 0.9
    assert result.metadata["model"] == "claude-sonnet"

    # Test with invalid input
    result = safe_parse_checker_output("invalid")
    assert result is None


def test_sanity_check_writer_output():
    """Test sanity checks for WriterOutput (warnings only)."""
    # Test with valid output
    valid_output = WriterOutput(
        paragraphs=[
            ModernizedParagraph(modern="Valid paragraph with content"),
            ModernizedParagraph(modern="Another valid paragraph"),
        ]
    )

    warnings = sanity_check_writer_output(valid_output)
    assert isinstance(warnings, list)
    # Should have no warnings for valid output

    # Test with empty output
    empty_output = WriterOutput(paragraphs=[])
    warnings = sanity_check_writer_output(empty_output)
    assert isinstance(warnings, list)
    assert len(warnings) > 0
    assert "No paragraphs" in warnings[0]

    # Test with empty paragraphs
    empty_para_output = WriterOutput(
        paragraphs=[
            ModernizedParagraph(modern=""),
            ModernizedParagraph(modern="   "),
            ModernizedParagraph(modern="Valid content"),
        ]
    )

    warnings = sanity_check_writer_output(empty_para_output)
    assert isinstance(warnings, list)
    assert len(warnings) >= 2  # Should warn about empty paragraphs


def test_sanity_check_checker_output():
    """Test sanity checks for CheckerOutput (warnings only)."""
    # Test with valid output
    valid_output = CheckerOutput(
        fidelity_score=85, readability_grade=8.5, confidence=0.8
    )

    warnings = sanity_check_checker_output(valid_output)
    assert isinstance(warnings, list)
    # Should have no warnings for valid output

    # Test with extreme values
    extreme_output = CheckerOutput(
        fidelity_score=150,  # Outside typical range
        readability_grade=25,  # Outside typical range
        confidence=0.8,
    )

    warnings = sanity_check_checker_output(extreme_output)
    assert isinstance(warnings, list)
    assert len(warnings) >= 2
    assert "outside typical range" in warnings[0]
    assert "outside typical range" in warnings[1]

    # Test with None values (should be fine)
    none_output = CheckerOutput()
    warnings = sanity_check_checker_output(none_output)
    assert isinstance(warnings, list)
    # Should have no warnings for None values


def test_log_llm_decision():
    """Test LLM decision logging."""
    # Test with reasoning
    log_llm_decision("test_context", "test_decision", "test_reasoning")

    # Test without reasoning
    log_llm_decision("test_context", "test_decision")

    # Test with different data types
    log_llm_decision("test_context", {"score": 85, "confidence": 0.8})
    log_llm_decision("test_context", 42)
    log_llm_decision("test_context", True)


def test_llm_driven_qa_report():
    """Test QAReport with LLM-driven optional fields."""
    # Test with all None values
    report = QAReport()
    assert report.fidelity_score is None
    assert report.readability_grade is None
    assert report.readability_appropriate is None
    assert report.confidence is None
    assert report.llm_reasoning is None
    assert report.metadata == {}

    # Test with partial values
    report = QAReport(
        fidelity_score=85,
        confidence=0.8,
        llm_reasoning="Good modernization",
        metadata={"model": "claude-sonnet"},
    )
    assert report.fidelity_score == 85
    assert report.confidence == 0.8
    assert report.llm_reasoning == "Good modernization"
    assert report.metadata["model"] == "claude-sonnet"
    assert report.readability_grade is None  # LLM didn't provide this


def test_llm_driven_checker_output():
    """Test CheckerOutput with LLM-driven optional fields."""
    # Test with all None values
    output = CheckerOutput()
    assert output.fidelity_score is None
    assert output.readability_grade is None
    assert output.readability_appropriate is None
    assert output.formatting_preserved is None
    assert output.tone_consistent is None
    assert output.confidence is None
    assert output.llm_reasoning is None
    assert output.metadata == {}

    # Test with partial values
    output = CheckerOutput(
        fidelity_score=90,
        readability_grade=7.5,
        confidence=0.85,
        llm_reasoning="Excellent modernization with minor issues",
        metadata={"model": "claude-sonnet", "version": "4.5"},
    )
    assert output.fidelity_score == 90
    assert output.readability_grade == 7.5
    assert output.confidence == 0.85
    assert "minor issues" in output.llm_reasoning
    assert output.metadata["model"] == "claude-sonnet"
    assert output.formatting_preserved is None  # LLM didn't provide this


def test_qa_issue_optional_severity():
    """Test QAIssue with optional severity field."""
    # Test with default severity
    issue = QAIssue(type="test", description="Test issue")
    assert issue.severity == "medium"

    # Test with explicit severity
    issue = QAIssue(type="test", description="Test issue", severity="high")
    assert issue.severity == "high"

    # Test with None severity
    issue = QAIssue(type="test", description="Test issue", severity=None)
    assert issue.severity is None


def test_llm_driven_serialization():
    """Test serialization of LLM-driven models."""
    # Test CheckerOutput serialization
    output = CheckerOutput(
        fidelity_score=85,
        confidence=0.8,
        llm_reasoning="Good modernization",
        metadata={"model": "claude-sonnet"},
    )

    data = output.model_dump()
    assert data["fidelity_score"] == 85
    assert data["confidence"] == 0.8
    assert data["llm_reasoning"] == "Good modernization"
    assert data["metadata"]["model"] == "claude-sonnet"
    assert data["readability_grade"] is None

    # Test deserialization
    restored = CheckerOutput(**data)
    assert restored.fidelity_score == 85
    assert restored.confidence == 0.8
    assert restored.llm_reasoning == "Good modernization"
    assert restored.metadata["model"] == "claude-sonnet"
    assert restored.readability_grade is None


def test_soft_validation_approach():
    """Test soft validation - no hard failures."""
    # Test that models accept None values without validation errors
    output = CheckerOutput(
        fidelity_score=None,
        readability_grade=None,
        readability_appropriate=None,
        formatting_preserved=None,
        tone_consistent=None,
        quote_count_match=None,
        emphasis_preserved=None,
        literary_quality_maintained=None,
        historical_accuracy_preserved=None,
        confidence=None,
        llm_reasoning=None,
        metadata={},
        issues=[],
    )

    # Should not raise any validation errors
    assert output.fidelity_score is None
    assert output.readability_grade is None
    assert output.confidence is None
    assert output.llm_reasoning is None


def test_llm_reasoning_capture():
    """Test that LLM reasoning is properly captured."""
    output = CheckerOutput(
        fidelity_score=88,
        confidence=0.9,
        llm_reasoning="The modernization successfully preserves the original meaning while improving readability for modern audiences. The character development and plot progression remain intact.",
        metadata={"model": "claude-sonnet", "processing_time": 2.3, "tokens_used": 150},
    )

    assert output.fidelity_score == 88
    assert output.confidence == 0.9
    assert "preserves the original meaning" in output.llm_reasoning
    assert "improving readability" in output.llm_reasoning
    assert output.metadata["model"] == "claude-sonnet"
    assert output.metadata["processing_time"] == 2.3
    assert output.metadata["tokens_used"] == 150


def test_metadata_flexibility():
    """Test metadata field flexibility."""
    # Test with various metadata types
    output = CheckerOutput(
        metadata={
            "string": "test",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }
    )

    assert output.metadata["string"] == "test"
    assert output.metadata["number"] == 42
    assert output.metadata["boolean"] is True
    assert output.metadata["list"] == [1, 2, 3]
    assert output.metadata["nested"]["key"] == "value"


def test_issues_list_flexibility():
    """Test issues list flexibility."""
    # Test with various issue types
    output = CheckerOutput(
        issues=[
            QAIssue(type="formatting", description="Missing quote", severity="medium"),
            QAIssue(type="content", description="Minor meaning change", severity="low"),
            QAIssue(type="style", description="Tone inconsistency", severity="high"),
            QAIssue(type="technical", description="Parse error", severity=None),
        ]
    )

    assert len(output.issues) == 4
    assert output.issues[0].type == "formatting"
    assert output.issues[1].severity == "low"
    assert output.issues[2].severity == "high"
    assert output.issues[3].severity is None
