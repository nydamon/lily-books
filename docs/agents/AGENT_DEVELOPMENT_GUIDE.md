# Agent Development Guide

How to create and maintain Claude Code subject-matter expert agents for Lily Books.

## Overview

Subject agents provide specialized expertise in specific domains of the codebase. Each agent consists of:

1. **Slash Command** (`.claude/commands/{agent}.md`) - Compact activation prompt
2. **Detailed Documentation** (`.claude/agents/{agent}.md`) - Comprehensive knowledge base
3. **Tests** (`tests/test_agents.py`) - Validation

## Agent Structure

### Slash Command Format

**File**: `.claude/commands/{agent}.md`

**Template**:
```markdown
You are now the **{Agent Name} Expert** for the Lily Books project.

You have deep expertise in {domain}.

## Your Core Knowledge

### {Topic 1}
- Key point 1
- Key point 2

### {Topic 2}
- Key point 1
- Key point 2

## Key Files You Know

- [file1.py](../src/lily_books/file1.py) - Description
- [file2.py](../src/lily_books/file2.py) - Description

## Common Tasks You Help With

1. **Task 1**: Description
2. **Task 2**: Description

## Your Approach

- Guideline 1
- Guideline 2

You are ready to answer questions and help with {domain} tasks.
```

**Guidelines**:
- Keep concise (< 5KB)
- Focus on activation context
- Link to detailed documentation
- Use relative paths

### Detailed Documentation Format

**File**: `.claude/agents/{agent}.md`

**Template**:
```markdown
# {Agent Name} Agent

**Command**: `/{agent}`

## Purpose

{One-sentence description}

## Key Knowledge Areas

### 1. {Area 1}

{Detailed explanation}

**Key Files**:
- [file.py:line](../../src/lily_books/file.py#Lline) - Description

**Usage**:
```python
# Code example
```

### 2. {Area 2}

...

## Key Files

{Complete list with links}

## Common Questions

### Q: {Question 1}

**Answer**:

{Detailed answer with examples}

### Q: {Question 2}

...

## Best Practices

### 1. {Practice 1}
{Description}

### 2. {Practice 2}
{Description}

## Related Agents

- [/{related-agent}]({related-agent}.md) - {Why related}

---

**Last Updated**: {Date}
**Version**: {Version}
```

**Guidelines**:
- Comprehensive (10-20KB)
- Include line number references
- Provide code examples
- Link to related agents
- Answer common questions

## Creating a New Agent

### Step 1: Identify Domain

**Good Domains**:
- Clear expertise boundary
- 3+ key files
- Distinct from other agents
- Common questions/tasks

**Bad Domains**:
- Too broad (overlaps multiple agents)
- Too narrow (1-2 files only)
- Rarely accessed
- Better handled by existing agent

### Step 2: Create Slash Command

```bash
touch .claude/commands/my-agent.md
```

Fill with activation context (use template above).

### Step 3: Create Detailed Documentation

```bash
touch .claude/agents/my-agent.md
```

Include:
- Purpose statement
- Key knowledge areas (3-7)
- Common questions (5-10)
- Best practices (3-5)
- Related agents

### Step 4: Update Master Index

**claude.md**:
```markdown
#### `/my-agent` - My Agent Expert
Expert in {domain}.

**Use when**: {scenarios}

**Key Areas**: {topics}

**Documentation**: [.claude/agents/my-agent.md](.claude/agents/my-agent.md)
```

**.claude/agents/README.md**:
```markdown
### N. My Agent
**Command**: `/my-agent`
**File**: [my-agent.md](my-agent.md)
**Expertise**: {Domain}

**Key Capabilities**:
- Capability 1
- Capability 2
```

### Step 5: Add Tests

**tests/test_agents.py**:
```python
# Add to AGENT_COMMANDS list
AGENT_COMMANDS = [
    ...,
    "my-agent",
]
```

Tests automatically verify:
- Slash command exists
- Detailed documentation exists
- Required sections present

### Step 6: Validate

```bash
# Run tests
poetry run pytest tests/test_agents.py -v

# Test invocation
# In Claude Code, type: /my-agent
```

## Maintaining Agents

### When to Update

**File Changes**:
- New files added to agent's domain
- File paths change
- Line numbers shift significantly

**Feature Changes**:
- New capabilities added
- Behavior changes
- Configuration options added

**Common Questions**:
- Users frequently ask new questions
- Existing answers become outdated

### How to Update

1. **Update slash command** if activation context changes
2. **Update detailed documentation**:
   - Add new sections
   - Update line numbers
   - Add new questions
   - Update code examples
3. **Update master index** if purpose changes
4. **Run tests** to validate
5. **Commit** with descriptive message

### Version Control

- Increment version number in detailed docs
- Update "Last Updated" date
- Document changes in commit message

## Best Practices

### 1. Keep Slash Commands Concise
- < 5KB file size
- Focus on activation
- Link to details

### 2. Make Documentation Comprehensive
- 10-20KB per agent
- Real code examples
- Line number references
- Common questions answered

### 3. Use Relative Paths
```markdown
[file.py](../../src/lily_books/file.py)  # Good
[file.py](/Users/user/lily-books/src/...)  # Bad
```

### 4. Link to Line Numbers
```markdown
[graph.py:100-150](../../src/lily_books/graph.py#L100-L150)
```

### 5. Cross-Reference Related Agents
```markdown
## Related Agents
- [/other-agent](other-agent.md) - For related tasks
```

### 6. Answer Real Questions
- Monitor user questions
- Add to "Common Questions"
- Provide working examples

### 7. Test Proactive Invocation
- Ensure Claude detects when agent needed
- Update activation context if not triggered

## Agent Categories

### Tier 1: Core Pipeline
- Most critical functionality
- Frequently accessed
- Complex domains

### Tier 2: Quality & Testing
- High-value supporting functions
- Important but not core
- Moderate complexity

### Tier 3: Media & Format
- Specialized domains
- Less frequently accessed
- Nice to have

## Examples

**Good Agent**:
- Clear domain (LangGraph pipeline)
- 5-7 knowledge areas
- 8-10 common questions
- Well-linked to related agents

**Needs Improvement**:
- Too broad (covers 3 agent domains)
- No code examples
- No line number references
- Missing common questions

## Troubleshooting

### Agent Not Triggered Proactively

**Fix**: Update slash command with clearer activation context

### Agent Gives Wrong Information

**Fix**: Update detailed documentation with corrections

### Tests Failing

**Fix**: Ensure required sections present in documentation

## Resources

- **Master Index**: `claude.md`
- **Agent Catalog**: `.claude/agents/README.md`
- **Test Suite**: `tests/test_agents.py`
- **This Guide**: `docs/agents/AGENT_DEVELOPMENT_GUIDE.md`

---

**Last Updated**: 2025-10-25
**Version**: 1.0
