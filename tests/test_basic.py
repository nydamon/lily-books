"""Basic tests to verify the setup."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lily_books.models import QAIssue, QAReport, ParaPair
from lily_books.config import get_project_paths


def test_qa_issue_model():
    """Test QAIssue model creation."""
    issue = QAIssue(
        type="test",
        description="Test issue",
        severity="low"
    )
    assert issue.type == "test"
    assert issue.severity == "low"


def test_qa_report_model():
    """Test QAReport model creation."""
    report = QAReport(
        fidelity_score=95,
        readability_grade=8.0,
        character_count_ratio=1.2
    )
    assert report.fidelity_score == 95
    assert report.readability_grade == 8.0


def test_para_pair_model():
    """Test ParaPair model creation."""
    pair = ParaPair(
        i=0,
        para_id="test_para",
        orig="Original text",
        modern="Modern text"
    )
    assert pair.i == 0
    assert pair.para_id == "test_para"
    assert pair.orig == "Original text"


def test_project_paths():
    """Test project paths generation."""
    paths = get_project_paths("test-slug")
    assert "base" in paths
    assert "work" in paths
    assert "meta" in paths
    assert paths["base"].name == "test-slug"
