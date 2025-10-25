# Lily Books Agent System

Comprehensive subject-matter expert agents for the Lily Books codebase.

## Agent Catalog

### 1. LangGraph Pipeline Agent
**Command**: `/langgraph-pipeline`
**File**: [langgraph-pipeline.md](langgraph-pipeline.md)
**Expertise**: State machine architecture, node orchestration, pipeline flow

**Key Capabilities**:
- Adding/modifying graph nodes
- Conditional routing logic
- State management (FlowState)
- Checkpointing and persistence
- Async processing patterns
- Feature toggle configuration

---

### 2. LLM Chains Agent
**Command**: `/llm-chains`
**File**: [llm-chains.md](llm-chains.md)
**Expertise**: LangChain best practices, LLM orchestration, cost optimization

**Key Capabilities**:
- Writer chain (text modernization)
- Checker chain (QA validation)
- Structured outputs with Pydantic
- LLM caching strategies
- Token counting and context management
- Fallback model configuration
- Langfuse observability

---

### 3. Publishing Pipeline Agent
**Command**: `/publishing`
**File**: [publishing.md](publishing.md)
**Expertise**: Publishing and distribution workflow

**Key Capabilities**:
- **PublishDrive integration (PRIMARY)** - manual upload
- **Draft2Digital API (BACKUP)** - deprecated
- **Amazon KDP (BACKUP)** - deprecated stub
- **Google Play Books (BACKUP)** - deprecated stub
- Identifier assignment (ASIN, ISBN, Google ID)
- Edition preparation (Kindle + Universal)
- SEO metadata generation
- Pricing optimization

---

### 4. Quality Assurance Agent
**Command**: `/qa-validation`
**File**: [qa-validation.md](qa-validation.md)
**Expertise**: Text QA, validation gates, quality metrics

**Key Capabilities**:
- Fidelity scoring (target: ≥92/100)
- Readability metrics (Flesch-Kincaid 7-9)
- Format preservation checks
- Soft vs hard validation
- Graduated quality gates
- Remediation strategies
- Quality control overrides

---

### 5. Testing & Reliability Agent
**Command**: `/testing`
**File**: [testing.md](testing.md)
**Expertise**: Testing, error handling, resilience patterns

**Key Capabilities**:
- Pytest test suite (51 Python files)
- Circuit breaker patterns
- Retry logic with exponential backoff
- Self-healing error recovery
- Failure modes and error tracking
- Langfuse debugging
- Mock and fixture patterns

---

### 6. Audio Production Agent
**Command**: `/audio-production`
**File**: [audio-production.md](audio-production.md)
**Expertise**: TTS and audio mastering workflow

**Key Capabilities**:
- Fish Audio TTS integration
- ACX compliance (RMS -20dB, peak -3dB)
- Audio mastering with ffmpeg
- Retail sample extraction
- Audio metrics calculation
- Voice model selection
- Cost estimation

---

### 7. EPUB & Cover Generation Agent
**Command**: `/epub-covers`
**File**: [epub-covers.md](epub-covers.md)
**Expertise**: Ebook creation and cover design

**Key Capabilities**:
- EPUB structure with ebooklib
- Metadata embedding
- Navigation and TOC generation
- Ideogram AI cover generation
- Cover validation
- EPUB validation with epubcheck
- Publishing metadata integration

---

## Usage Patterns

### Proactive Invocation
Agents are **automatically invoked** by Claude when their expertise is needed. You don't need to manually invoke them unless you want to.

### Multi-Agent Collaboration
For complex tasks, Claude may invoke multiple agents simultaneously:

**Example**: Adding a new publishing validation step
- Invokes `/langgraph-pipeline` to understand graph structure
- Invokes `/publishing` to understand validation requirements
- Combines knowledge to provide comprehensive solution

---

## Agent Structure

Each agent contains:

1. **Purpose Statement**: High-level role and expertise
2. **Key Knowledge Areas**: Specific domains of expertise
3. **Key Files**: Relevant source files with line numbers
4. **Common Questions**: Frequently asked questions and solutions
5. **Best Practices**: Recommended patterns and approaches
6. **Related Agents**: Cross-references to complementary agents

---

## Development

### Creating New Agents
See [AGENT_DEVELOPMENT_GUIDE.md](../../docs/agents/AGENT_DEVELOPMENT_GUIDE.md)

### Testing Agents
See [AGENT_TESTING.md](../../docs/agents/AGENT_TESTING.md)

---

## Maintenance

Agents should be updated when:
- New features are added to the codebase
- File structures change significantly
- Common questions evolve
- Best practices are updated

---

**Version**: 1.0
**Last Updated**: 2025-10-25
**Branch**: `feature/claude-subject-agents`
