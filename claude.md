# Claude Code Agent System - Lily Books

This file serves as the master reference for the Lily Books Claude Code agent system.

## Overview

Lily Books uses a subject-matter expert agent system to provide specialized knowledge across different areas of the codebase. Each agent is accessible via slash commands and provides deep expertise in specific domains.

## Available Agents

### Tier 1: Core Pipeline Agents

#### `/langgraph-pipeline` - LangGraph Pipeline Expert
Expert in state machine architecture, node orchestration, and pipeline flow control.

**Use when**: Modifying graph structure, adding nodes, routing logic, state management

**Key Areas**: Graph nodes, conditional edges, FlowState, checkpointing, async processing

**Documentation**: [.claude/agents/langgraph-pipeline.md](.claude/agents/langgraph-pipeline.md)

---

#### `/llm-chains` - LLM Chains Expert
Expert in LangChain best practices, LLM orchestration, and cost optimization.

**Use when**: Working with Writer/Checker chains, optimizing tokens, debugging LLM calls

**Key Areas**: Structured outputs, caching, fallback models, Langfuse observability

**Documentation**: [.claude/agents/llm-chains.md](.claude/agents/llm-chains.md)

---

#### `/publishing` - Publishing Pipeline Expert
Expert in publishing and distribution workflow, including PublishDrive (primary) and legacy integrations.

**Use when**: Publishing setup, retailer uploads, metadata optimization, ISBN assignment

**Key Areas**: PublishDrive manual upload, Draft2Digital API (backup), SEO metadata, pricing

**Documentation**: [.claude/agents/publishing.md](.claude/agents/publishing.md)

**Important**: PublishDrive is the primary distributor (manual upload). Draft2Digital, Amazon KDP, and Google Play Books are deprecated but kept as backups.

---

### Tier 2: Quality & Testing Agents

#### `/qa-validation` - Quality Assurance Expert
Expert in text QA, validation gates, and quality metrics.

**Use when**: Debugging QA failures, adjusting quality thresholds, remediation strategies

**Key Areas**: Fidelity scoring, readability metrics, soft/hard validation, graduated gates

**Documentation**: [.claude/agents/qa-validation.md](.claude/agents/qa-validation.md)

---

#### `/testing` - Testing & Reliability Expert
Expert in testing, error handling, and resilience patterns.

**Use when**: Writing tests, debugging failures, implementing retry logic, circuit breakers

**Key Areas**: Pytest patterns, self-healing errors, observability, mocking

**Documentation**: [.claude/agents/testing.md](.claude/agents/testing.md)

---

### Tier 3: Media & Format Agents

#### `/audio-production` - Audio Production Expert
Expert in TTS and audio mastering workflow.

**Use when**: Fish Audio integration, ACX compliance, audio mastering, cost estimation

**Key Areas**: TTS generation, audio metrics, mastering pipeline, retail samples

**Documentation**: [.claude/agents/audio-production.md](.claude/agents/audio-production.md)

---

#### `/epub-covers` - EPUB & Cover Generation Expert
Expert in ebook creation and cover design.

**Use when**: EPUB formatting, cover generation, metadata embedding, validation

**Key Areas**: ebooklib, Ideogram AI covers, EPUB validation, publishing metadata

**Documentation**: [.claude/agents/epub-covers.md](.claude/agents/epub-covers.md)

---

## How to Use

### Manual Invocation
Type the slash command to activate an agent:
```
/langgraph-pipeline
```

Claude will then have deep context about that domain and can answer questions or help with tasks.

### Automatic Invocation
Claude will **automatically detect** when specialist knowledge is needed and invoke the appropriate agent(s) proactively. You don't need to remember command names - just ask your question naturally.

**Example**:
```
You: "How do I add a new validation node before publishing?"

Claude: [Automatically invokes /langgraph-pipeline and /publishing]
        [Provides comprehensive answer using combined knowledge]
```

---

## Agent Architecture

### Slash Commands
Each agent has a **slash command file** in `.claude/commands/{agent}.md` that gets loaded when invoked.

### Detailed Documentation
Each agent has **detailed documentation** in `.claude/agents/{agent}.md` with:
- Key knowledge areas
- Relevant files and line numbers
- Common questions and solutions
- Best practices and patterns

### Master Index
This file (`claude.md`) serves as the **master index** of all available agents.

---

## Development Guides

- **[Agent Development Guide](docs/agents/AGENT_DEVELOPMENT_GUIDE.md)**: How to create and maintain agents
- **[Agent Testing Guide](docs/agents/AGENT_TESTING.md)**: Testing strategy and validation
- **[Agent Index](.claude/agents/README.md)**: Detailed agent capabilities

---

## Project Context

**Lily Books** is a LangGraph-based pipeline for modernizing public domain books with:
- Text modernization (GPT-4o-mini)
- Quality validation (Claude 4.5 Haiku)
- EPUB generation
- AI cover creation (Ideogram)
- Audio production (Fish Audio TTS)
- Publishing distribution (PublishDrive primary, D2D/KDP/Google backup)

**Tech Stack**: LangChain, LangGraph, OpenRouter, Langfuse, ebooklib, Fish Audio

**Repository**: `/Users/damondecrescenzo/Lily books`

---

## Quick Reference

| Task | Agent | Command |
|------|-------|---------|
| Add graph node | LangGraph Pipeline | `/langgraph-pipeline` |
| Optimize LLM costs | LLM Chains | `/llm-chains` |
| Setup publishing | Publishing Pipeline | `/publishing` |
| Fix QA failures | Quality Assurance | `/qa-validation` |
| Write tests | Testing & Reliability | `/testing` |
| Audio mastering | Audio Production | `/audio-production` |
| EPUB validation | EPUB & Covers | `/epub-covers` |

---

## Recent Updates

### 2025-10-25: Claude Code Agent System
- **Added 7 subject-matter expert agents** for specialized codebase knowledge
- Agents cover: LangGraph pipeline, LLM chains, publishing, QA, testing, audio, EPUB/covers
- Comprehensive documentation with 60KB+ of detailed agent knowledge
- Automatic agent invocation for proactive assistance
- Development and testing guides included

### 2025-10-25: PublishDrive Integration
- **Pivoted to PublishDrive** as primary distribution platform
- PublishDrive distributes to 400+ stores (Amazon, Apple, Google, Kobo, B&N, etc.)
- Provides free ISBN and unified analytics dashboard
- Manual upload process (Selenium automation planned for future)
- **Legacy systems preserved**: Draft2Digital, Amazon KDP, Google Play Books marked as DEPRECATED but remain functional as backups
- Updated graph routing to prioritize PublishDrive
- Added comprehensive PublishDrive quick start guide ([docs/PUBLISHDRIVE_QUICKSTART.md](docs/PUBLISHDRIVE_QUICKSTART.md))

**Files Modified:**
- `src/lily_books/tools/uploaders/publishdrive.py` (new)
- `src/lily_books/config.py` (PublishDrive credentials)
- `src/lily_books/graph.py` (PublishDrive-first routing)
- `src/lily_books/tools/identifiers.py` (PublishDrive edition support)
- All legacy uploaders marked with deprecation warnings

**How to use:**
```bash
# .env
TARGET_RETAILERS=publishdrive  # Recommended (PRIMARY)
# or
TARGET_RETAILERS=draft2digital,amazon,google  # Legacy (BACKUP)
```

---

**Last Updated**: 2025-10-25
**Version**: 1.2
**Branch**: `main`
