"""Tests for Claude Code agent slash commands."""

import pytest
from pathlib import Path


class TestAgentSlashCommands:
    """Test that all agent slash commands exist."""

    AGENT_COMMANDS = [
        "langgraph-pipeline",
        "llm-chains",
        "publishing",
        "qa-validation",
        "audio-production",
        "epub-covers",
        "testing",
    ]

    @pytest.mark.parametrize("agent", AGENT_COMMANDS)
    def test_slash_command_exists(self, agent):
        """Verify slash command file exists for each agent."""
        command_path = Path(f".claude/commands/{agent}.md")
        assert command_path.exists(), f"Slash command file missing: {command_path}"

    @pytest.mark.parametrize("agent", AGENT_COMMANDS)
    def test_agent_documentation_exists(self, agent):
        """Verify detailed documentation exists for each agent."""
        doc_path = Path(f".claude/agents/{agent}.md")
        assert doc_path.exists(), f"Agent documentation missing: {doc_path}"

    @pytest.mark.parametrize("agent", AGENT_COMMANDS)
    def test_agent_documentation_complete(self, agent):
        """Verify agent documentation has required sections."""
        doc_path = Path(f".claude/agents/{agent}.md")
        content = doc_path.read_text()

        required_sections = [
            "## Purpose",
            "## Key Knowledge Areas",
            "## Key Files",
            "## Common Questions",
        ]

        for section in required_sections:
            assert (
                section in content
            ), f"Agent {agent} missing section: {section}"

    def test_master_claude_md_exists(self):
        """Verify master claude.md exists at project root."""
        claude_md = Path("claude.md")
        assert claude_md.exists(), "Master claude.md missing at project root"

    def test_master_claude_md_references_all_agents(self):
        """Verify master claude.md references all agents."""
        claude_md = Path("claude.md")
        content = claude_md.read_text()

        for agent in self.AGENT_COMMANDS:
            slash_command = f"/{agent}"
            assert (
                slash_command in content
            ), f"claude.md missing reference to {slash_command}"

    def test_agents_readme_exists(self):
        """Verify .claude/agents/README.md exists."""
        readme = Path(".claude/agents/README.md")
        assert readme.exists(), "Agents README missing: .claude/agents/README.md"


class TestPublishingAgentContext:
    """Test that Publishing Agent has correct PublishDrive context."""

    def test_publishing_agent_mentions_publishdrive(self):
        """Verify Publishing Agent references PublishDrive as primary."""
        doc_path = Path(".claude/agents/publishing.md")
        content = doc_path.read_text()

        assert (
            "PublishDrive" in content
        ), "Publishing Agent must mention PublishDrive"
        assert (
            "primary" in content.lower() or "PRIMARY" in content
        ), "Publishing Agent must indicate PublishDrive is primary"

    def test_publishing_agent_mentions_legacy_integrations(self):
        """Verify Publishing Agent references legacy integrations as backups."""
        doc_path = Path(".claude/agents/publishing.md")
        content = doc_path.read_text()

        # Should mention legacy integrations
        assert "Draft2Digital" in content, "Publishing Agent must mention D2D"
        assert (
            "Amazon KDP" in content or "KDP" in content
        ), "Publishing Agent must mention Amazon KDP"
        assert (
            "Google Play" in content
        ), "Publishing Agent must mention Google Play Books"

        # Should indicate they are deprecated/backup
        assert (
            "deprecated" in content.lower()
            or "backup" in content.lower()
            or "BACKUP" in content
        ), "Publishing Agent must indicate legacy integrations are backups"


class TestAgentFileReferences:
    """Test that agents reference correct files."""

    def test_langgraph_agent_references_graph_py(self):
        """Verify LangGraph Agent references graph.py."""
        doc_path = Path(".claude/agents/langgraph-pipeline.md")
        content = doc_path.read_text()
        assert "graph.py" in content, "LangGraph Agent must reference graph.py"

    def test_llm_chains_agent_references_chains(self):
        """Verify LLM Chains Agent references chain files."""
        doc_path = Path(".claude/agents/llm-chains.md")
        content = doc_path.read_text()
        assert (
            "writer.py" in content
        ), "LLM Chains Agent must reference writer.py"
        assert (
            "checker.py" in content
        ), "LLM Chains Agent must reference checker.py"

    def test_publishing_agent_references_uploaders(self):
        """Verify Publishing Agent references uploader files."""
        doc_path = Path(".claude/agents/publishing.md")
        content = doc_path.read_text()
        assert (
            "uploaders" in content
        ), "Publishing Agent must reference uploaders directory"


class TestDevelopmentGuides:
    """Test that development guides exist."""

    def test_agent_development_guide_exists(self):
        """Verify AGENT_DEVELOPMENT_GUIDE.md exists."""
        guide = Path("docs/agents/AGENT_DEVELOPMENT_GUIDE.md")
        assert guide.exists(), "AGENT_DEVELOPMENT_GUIDE.md missing"

    def test_agent_testing_guide_exists(self):
        """Verify AGENT_TESTING.md exists."""
        guide = Path("docs/agents/AGENT_TESTING.md")
        assert guide.exists(), "AGENT_TESTING.md missing"
