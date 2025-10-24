"""Tests for Pydantic data models."""

from lily_books.models import (
    BookMetadata,
    ChapterDoc,
    ChapterSplit,
    CheckerOutput,
    ModernizedParagraph,
    ParaPair,
    QAIssue,
    QAReport,
    WriterOutput,
)


def test_qa_issue():
    """Test QAIssue model."""
    issue = QAIssue(type="formatting", description="Missing quote", severity="medium")

    assert issue.type == "formatting"
    assert issue.description == "Missing quote"
    assert issue.severity == "medium"
    assert issue.span_original is None
    assert issue.suggestion is None


def test_qa_report():
    """Test QAReport model."""
    report = QAReport(
        fidelity_score=95,
        readability_grade=8.5,
        character_count_ratio=1.2,
        modernization_complete=True,
        formatting_preserved=True,
        tone_consistent=True,
        quote_count_match=True,
        emphasis_preserved=True,
        retry_count=0,
    )

    assert report.fidelity_score == 95
    assert report.readability_grade == 8.5
    assert report.character_count_ratio == 1.2
    assert report.modernization_complete is True
    assert len(report.issues) == 0


def test_para_pair():
    """Test ParaPair model."""
    pair = ParaPair(
        i=0,
        para_id="ch01_para000",
        orig="It is a truth universally acknowledged.",
        modern="It is a truth universally acknowledged.",
    )

    assert pair.i == 0
    assert pair.para_id == "ch01_para000"
    assert pair.orig == "It is a truth universally acknowledged."
    assert pair.modern == "It is a truth universally acknowledged."
    assert pair.qa is None
    assert pair.notes is None


def test_chapter_split():
    """Test ChapterSplit model."""
    chapter = ChapterSplit(
        chapter=1,
        title="Chapter 1",
        paragraphs=[
            "It is a truth universally acknowledged.",
            "That a single man in possession of a good fortune.",
        ],
    )

    assert chapter.chapter == 1
    assert chapter.title == "Chapter 1"
    assert len(chapter.paragraphs) == 2
    assert chapter.paragraphs[0] == "It is a truth universally acknowledged."


def test_chapter_doc():
    """Test ChapterDoc model."""
    pair1 = ParaPair(
        i=0, para_id="ch01_para000", orig="Original text", modern="Modern text"
    )
    pair2 = ParaPair(
        i=1, para_id="ch01_para001", orig="More text", modern="More modern text"
    )

    doc = ChapterDoc(chapter=1, title="Chapter 1", pairs=[pair1, pair2])

    assert doc.chapter == 1
    assert doc.title == "Chapter 1"
    assert len(doc.pairs) == 2
    assert doc.pairs[0].para_id == "ch01_para000"


def test_book_metadata():
    """Test BookMetadata model."""
    metadata = BookMetadata(
        title="Pride and Prejudice (Modernized)",
        author="Jane Austen",
        public_domain_source="Project Gutenberg #1342",
    )

    assert metadata.title == "Pride and Prejudice (Modernized)"
    assert metadata.author == "Jane Austen"
    assert metadata.public_domain_source == "Project Gutenberg #1342"
    assert metadata.language == "en-US"
    assert metadata.voice["provider"] == "fish_audio"
    assert metadata.acx["target_rms_db"] == -20


def test_model_serialization():
    """Test model serialization and deserialization."""
    issue = QAIssue(type="test", description="Test issue", severity="low")

    # Test serialization
    data = issue.model_dump()
    assert data["type"] == "test"
    assert data["description"] == "Test issue"
    assert data["severity"] == "low"

    # Test deserialization
    restored = QAIssue(**data)
    assert restored.type == issue.type
    assert restored.description == issue.description
    assert restored.severity == issue.severity


def test_modernized_paragraph():
    """Test ModernizedParagraph model."""
    para = ModernizedParagraph(modern="Modernized text content")

    assert para.modern == "Modernized text content"


def test_writer_output():
    """Test WriterOutput model."""
    output = WriterOutput(
        paragraphs=[
            ModernizedParagraph(modern="First paragraph"),
            ModernizedParagraph(modern="Second paragraph"),
        ]
    )

    assert len(output.paragraphs) == 2
    assert output.paragraphs[0].modern == "First paragraph"
    assert output.paragraphs[1].modern == "Second paragraph"


def test_checker_output():
    """Test CheckerOutput model with LLM-driven optional fields."""
    output = CheckerOutput(
        fidelity_score=95,
        readability_grade=8.5,
        readability_appropriate=True,
        formatting_preserved=True,
        tone_consistent=True,
        quote_count_match=True,
        emphasis_preserved=True,
        confidence=0.92,
        llm_reasoning="The modernization preserves the original meaning while improving readability.",
        metadata={"source": "claude-sonnet", "processing_time": 2.3},
        issues=[
            QAIssue(type="formatting", description="Missing quote", severity="medium")
        ],
    )

    assert output.fidelity_score == 95
    assert output.readability_grade == 8.5
    assert output.readability_appropriate is True
    assert output.formatting_preserved is True
    assert output.tone_consistent is True
    assert output.quote_count_match is True
    assert output.emphasis_preserved is True
    assert output.confidence == 0.92
    assert "preserves the original meaning" in output.llm_reasoning
    assert output.metadata["source"] == "claude-sonnet"
    assert len(output.issues) == 1
    assert output.issues[0].type == "formatting"


def test_checker_output_optional_fields():
    """Test CheckerOutput with optional fields (LLM-driven approach)."""
    # Test with all None values (LLM decides)
    output = CheckerOutput()
    assert output.fidelity_score is None
    assert output.readability_grade is None
    assert output.readability_appropriate is None
    assert output.formatting_preserved is None
    assert output.tone_consistent is None
    assert output.quote_count_match is None
    assert output.emphasis_preserved is None
    assert output.confidence is None
    assert output.llm_reasoning is None
    assert output.metadata == {}
    assert output.issues == []

    # Test with partial values
    output = CheckerOutput(
        fidelity_score=85, confidence=0.8, llm_reasoning="Partial assessment"
    )
    assert output.fidelity_score == 85
    assert output.confidence == 0.8
    assert output.llm_reasoning == "Partial assessment"
    assert output.readability_grade is None
    assert output.readability_appropriate is None


def test_writer_output_serialization():
    """Test WriterOutput serialization."""
    output = WriterOutput(paragraphs=[ModernizedParagraph(modern="Test paragraph")])

    data = output.model_dump()
    assert "paragraphs" in data
    assert len(data["paragraphs"]) == 1
    assert data["paragraphs"][0]["modern"] == "Test paragraph"

    # Test deserialization
    restored = WriterOutput(**data)
    assert len(restored.paragraphs) == 1
    assert restored.paragraphs[0].modern == "Test paragraph"


def test_checker_output_serialization():
    """Test CheckerOutput serialization with LLM fields."""
    output = CheckerOutput(
        fidelity_score=85,
        readability_grade=7.5,
        readability_appropriate=True,
        formatting_preserved=False,
        tone_consistent=True,
        quote_count_match=False,
        emphasis_preserved=True,
        confidence=0.88,
        llm_reasoning="Good modernization with minor formatting issues",
        metadata={"model": "claude-sonnet", "version": "4.5"},
        issues=[],
    )

    data = output.model_dump()
    assert data["fidelity_score"] == 85
    assert data["readability_grade"] == 7.5
    assert data["readability_appropriate"] is True
    assert data["formatting_preserved"] is False
    assert data["tone_consistent"] is True
    assert data["quote_count_match"] is False
    assert data["emphasis_preserved"] is True
    assert data["confidence"] == 0.88
    assert "minor formatting issues" in data["llm_reasoning"]
    assert data["metadata"]["model"] == "claude-sonnet"
    assert data["issues"] == []

    # Test deserialization
    restored = CheckerOutput(**data)
    assert restored.fidelity_score == 85
    assert restored.readability_grade == 7.5
    assert restored.readability_appropriate is True
    assert restored.formatting_preserved is False
    assert restored.confidence == 0.88
    assert restored.metadata["model"] == "claude-sonnet"


def test_qa_report_optional_fields():
    """Test QAReport with optional fields."""
    report = QAReport()
    assert report.fidelity_score is None
    assert report.readability_grade is None
    assert report.readability_appropriate is None
    assert report.character_count_ratio is None
    assert report.modernization_complete is None
    assert report.formatting_preserved is None
    assert report.tone_consistent is None
    assert report.quote_count_match is None
    assert report.emphasis_preserved is None
    assert report.literary_quality_maintained is None
    assert report.historical_accuracy_preserved is None
    assert report.confidence is None
    assert report.llm_reasoning is None
    assert report.metadata == {}
    assert report.issues == []
    assert report.retry_count == 0


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
