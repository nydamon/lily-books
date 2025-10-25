# Agent Testing Guide

Comprehensive testing strategy for Claude Code subject-matter expert agents.

## Overview

Agent testing ensures:
1. All agents exist and are accessible
2. Documentation is complete and accurate
3. Knowledge is up-to-date
4. Proactive invocation works

## Test Structure

### Automated Tests

**File**: `tests/test_agents.py`

**Test Classes**:
1. `TestAgentSlashCommands` - Slash command existence
2. `TestPublishingAgentContext` - PublishDrive context validation
3. `TestAgentFileReferences` - File reference accuracy
4. `TestDevelopmentGuides` - Guide existence

### Running Tests

```bash
# All agent tests
poetry run pytest tests/test_agents.py -v

# Specific test class
poetry run pytest tests/test_agents.py::TestAgentSlashCommands -v

# Single test
poetry run pytest tests/test_agents.py::test_slash_command_exists -v
```

## Test Categories

### 1. Existence Tests

**Purpose**: Verify all required files exist

```python
def test_slash_command_exists(self, agent):
    """Verify slash command file exists for each agent."""
    command_path = Path(f".claude/commands/{agent}.md")
    assert command_path.exists()

def test_agent_documentation_exists(self, agent):
    """Verify detailed documentation exists for each agent."""
    doc_path = Path(f".claude/agents/{agent}.md")
    assert doc_path.exists()
```

**Coverage**:
- Slash commands (`.claude/commands/*.md`)
- Detailed docs (`.claude/agents/*.md`)
- Master index (`claude.md`)
- Agent catalog (`.claude/agents/README.md`)
- Development guides

### 2. Completeness Tests

**Purpose**: Ensure required sections present

```python
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
        assert section in content
```

**Required Sections**:
- Purpose statement
- Key Knowledge Areas
- Key Files list
- Common Questions
- Best Practices (recommended)
- Related Agents (recommended)

### 3. Context Validation Tests

**Purpose**: Verify agent-specific context

**Example**: Publishing Agent PublishDrive Context

```python
def test_publishing_agent_mentions_publishdrive(self):
    """Verify Publishing Agent references PublishDrive as primary."""
    doc_path = Path(".claude/agents/publishing.md")
    content = doc_path.read_text()

    assert "PublishDrive" in content
    assert "primary" in content.lower() or "PRIMARY" in content

def test_publishing_agent_mentions_legacy_integrations(self):
    """Verify Publishing Agent references legacy integrations."""
    doc_path = Path(".claude/agents/publishing.md")
    content = doc_path.read_text()

    assert "Draft2Digital" in content
    assert "deprecated" in content.lower() or "backup" in content.lower()
```

**Custom Validations**:
- Agent-specific terminology
- Key concepts mentioned
- Critical context present

### 4. File Reference Tests

**Purpose**: Ensure agents reference correct files

```python
def test_langgraph_agent_references_graph_py(self):
    """Verify LangGraph Agent references graph.py."""
    doc_path = Path(".claude/agents/langgraph-pipeline.md")
    content = doc_path.read_text()
    assert "graph.py" in content

def test_llm_chains_agent_references_chains(self):
    """Verify LLM Chains Agent references chain files."""
    doc_path = Path(".claude/agents/llm-chains.md")
    content = doc_path.read_text()
    assert "writer.py" in content
    assert "checker.py" in content
```

**Checks**:
- Key files mentioned
- File paths accurate
- Line numbers reasonable (not exact match)

## Manual Testing

### 1. Slash Command Invocation

**Test**: Type slash command in Claude Code

```
/langgraph-pipeline
```

**Expected**:
- Agent activates
- Provides specialized context
- Ready to answer domain questions

**Validate**:
- Activation message clear
- Context appropriate
- No errors

### 2. Question Answering

**Test**: Ask domain-specific questions

```
/langgraph-pipeline
How do I add a new node to the publishing pipeline?
```

**Expected**:
- Accurate answer
- References specific line numbers
- Provides code examples
- Suggests related agents if applicable

**Validate**:
- Information correct
- Code examples work
- Line numbers accurate

### 3. Proactive Invocation

**Test**: Ask question WITHOUT slash command

```
How do I add a new validation node before uploading to retailers?
```

**Expected**:
- Claude automatically invokes `/langgraph-pipeline`
- May also invoke `/publishing`
- Combines knowledge from both

**Validate**:
- Correct agents triggered
- No manual invocation needed
- Multi-agent collaboration works

### 4. Cross-Agent Integration

**Test**: Ask question spanning multiple agents

```
How do I optimize LLM token usage in the QA validation step?
```

**Expected**:
- Claude invokes `/llm-chains` (token optimization)
- May also invoke `/qa-validation` (QA specifics)
- Integrates knowledge seamlessly

**Validate**:
- Both agents contribute
- No contradictory information
- Comprehensive answer

## Testing Checklist

### New Agent Creation

- [ ] Slash command file exists
- [ ] Detailed documentation exists
- [ ] Master index updated (claude.md)
- [ ] Agent catalog updated (.claude/agents/README.md)
- [ ] Tests pass (`pytest tests/test_agents.py`)
- [ ] Manual invocation works
- [ ] Proactive invocation works
- [ ] Answers common questions accurately

### Agent Updates

- [ ] Slash command updated (if needed)
- [ ] Detailed documentation updated
- [ ] Line numbers refreshed
- [ ] New questions added
- [ ] Tests still pass
- [ ] Manual testing validates changes

### Regular Maintenance

**Monthly**:
- [ ] Review all agent docs for accuracy
- [ ] Update line numbers if files changed
- [ ] Add new common questions
- [ ] Test proactive invocation

**When Code Changes**:
- [ ] Update affected agents
- [ ] Refresh file references
- [ ] Add new capabilities to docs
- [ ] Re-run tests

## Test Development

### Adding New Tests

**For New Agent**:
1. Add to `AGENT_COMMANDS` list
2. Automatic coverage via parametrized tests
3. Add custom context tests if needed

**For Specific Validation**:
```python
class TestMyAgentContext:
    def test_my_agent_knows_key_concept(self):
        """Verify My Agent mentions key concept."""
        doc_path = Path(".claude/agents/my-agent.md")
        content = doc_path.read_text()
        assert "key_concept" in content
```

### Test Best Practices

1. **Parametrize Common Tests**:
```python
@pytest.mark.parametrize("agent", AGENT_COMMANDS)
def test_agent_exists(self, agent):
    # Test runs for each agent
```

2. **Clear Assertions**:
```python
assert "concept" in content, "Agent must mention concept"
```

3. **Test What Matters**:
- Existence (critical)
- Completeness (important)
- Context (agent-specific)
- File refs (helpful)

## Troubleshooting

### Test Failures

**"Slash command file missing"**:
- Create `.claude/commands/{agent}.md`
- Run tests again

**"Required section missing"**:
- Add section to `.claude/agents/{agent}.md`
- Follow documentation template

**"File reference not found"**:
- Update agent docs with correct file
- Verify file path accurate

### Agent Not Working

**Manual invocation fails**:
- Check slash command file exists
- Verify no syntax errors
- Review activation context

**Proactive invocation fails**:
- Enhance activation context
- Add more trigger keywords
- Test with clearer questions

**Wrong information provided**:
- Update detailed documentation
- Refresh line numbers
- Add corrections to common questions

## Continuous Integration

### Recommended CI Setup

```yaml
# .github/workflows/test-agents.yml
name: Test Agents

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Test agents
        run: poetry run pytest tests/test_agents.py -v
```

## Resources

- **Test Suite**: `tests/test_agents.py`
- **Development Guide**: `docs/agents/AGENT_DEVELOPMENT_GUIDE.md`
- **Agent Catalog**: `.claude/agents/README.md`
- **Master Index**: `claude.md`

---

**Last Updated**: 2025-10-25
**Version**: 1.0
