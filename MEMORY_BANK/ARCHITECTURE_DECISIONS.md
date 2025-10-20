# Architecture Decision Records (ADRs)

## ADR-001: LangChain Framework Selection

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for robust LLM orchestration and state management

### Decision
Use LangChain + LangGraph for the book modernization pipeline.

### Rationale
- **LangChain**: Mature ecosystem with extensive LLM integrations
- **LangGraph**: Persistent state management and checkpointing
- **Community**: Large community and documentation
- **Flexibility**: Supports complex workflows with human-in-the-loop

### Consequences
- **Positive**: Robust framework, extensive documentation, community support
- **Negative**: Learning curve, dependency on external framework
- **Neutral**: Standard choice for LLM applications

### Implementation
- State machine with 10 nodes orchestrated via LangGraph
- `SqliteSaver` for persistent state management
- Chain composition for LLM interactions

---

## ADR-002: Multi-Provider LLM Strategy

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for reliable LLM services with cost optimization

### Decision
Use OpenAI GPT-4o for modernization, Anthropic Claude Sonnet 4.5 for QA validation.

### Rationale
- **GPT-4o**: Excels at creative text transformation
- **Claude Sonnet 4.5**: Superior analytical capabilities for QA with latest intelligence
- **Redundancy**: Reduces single points of failure
- **Cost**: Model specialization for optimization

### Consequences
- **Positive**: Best-of-breed models for each task, redundancy
- **Negative**: Multiple API keys, vendor lock-in
- **Neutral**: Standard multi-provider approach

### Implementation
- GPT-4o for `rewrite_chapter()` function
- Claude Sonnet for `qa_chapter()` function
- Fallback models: GPT-4o-mini, Claude Haiku

---

## ADR-003: Two-Layer Persistence Strategy

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for reliable data persistence and pipeline resumption

### Decision
Use file-based storage for chapters + SQLite checkpoints for graph state.

### Rationale
- **Immediate Persistence**: Completed work saved immediately
- **Graph Recovery**: Pipeline state recovery for resumption
- **Human Review**: Readable chapter files for manual review
- **Atomic Operations**: Prevents data loss

### Consequences
- **Positive**: Reliable persistence, human-readable files
- **Negative**: Multiple storage systems, potential sync issues
- **Neutral**: Standard approach for complex workflows

### Implementation
- `books/{slug}/work/rewrite/ch{NN}.json` - Chapter documents
- `books/{slug}/meta/checkpoints.db` - LangGraph state
- `books/{slug}/meta/chapter_failures.jsonl` - Failure tracking

---

## ADR-004: Structured Outputs with Pydantic

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for type safety and better error handling

### Decision
Replace `JsonOutputParser()` with `PydanticOutputParser` using explicit schemas.

### Rationale
- **Type Safety**: Automatic validation and type checking
- **Error Handling**: Better error messages and debugging
- **Maintainability**: Clear data contracts
- **LangChain Best Practice**: Recommended approach

### Consequences
- **Positive**: Type safety, better errors, maintainability
- **Negative**: Additional schema maintenance
- **Neutral**: Standard practice for production systems

### Implementation
- `WriterOutput` schema for modernization responses
- `CheckerOutput` schema for QA validation
- Automatic validation and error handling

---

## ADR-005: LLM Response Caching

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for cost optimization and performance

### Decision
Implement semantic caching for LLM responses.

### Rationale
- **Cost Reduction**: 30-50% savings on QA reruns
- **Performance**: Faster responses for cached queries
- **Reliability**: Reduces API dependency
- **LangChain Best Practice**: Recommended for production

### Consequences
- **Positive**: Cost savings, performance improvement
- **Negative**: Cache management complexity
- **Neutral**: Standard optimization technique

### Implementation
- `InMemoryCache` for development
- `RedisSemanticCache` for production
- Configurable TTL and cache strategies

---

## ADR-006: Fallback Model Configuration

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for resilience and availability

### Decision
Use `RunnableWithFallbacks` pattern for model resilience.

### Rationale
- **Resilience**: Continue processing if primary model fails
- **Cost Optimization**: Fallback to cheaper models
- **Availability**: Handle rate limits and outages
- **LangChain Best Practice**: Recommended resilience pattern

### Consequences
- **Positive**: Improved reliability, cost optimization
- **Negative**: Additional configuration complexity
- **Neutral**: Standard resilience approach

### Implementation
- GPT-4o → GPT-4o-mini fallback
- Claude Sonnet 4.5 → Claude Haiku 4.5 fallback
- Automatic error handling and logging

---

## ADR-007: Token Counting and Context Management

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need to prevent context overflow errors

### Decision
Add explicit token validation before API calls.

### Rationale
- **Error Prevention**: Avoid context overflow errors
- **Optimization**: Adaptive batch sizing
- **Cost Control**: Efficient token usage
- **LangChain Best Practice**: Recommended for production

### Consequences
- **Positive**: Error prevention, optimization
- **Negative**: Additional complexity
- **Neutral**: Standard practice for LLM applications

### Implementation
- `tiktoken` integration for accurate counting
- Context window validation with safety margins
- Adaptive batch sizing based on token limits

---

## ADR-008: Advanced Retry Logic

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for robust error handling and rate limit management

### Decision
Use `tenacity` library for sophisticated retry strategies.

### Rationale
- **Rate Limits**: Better handling of API rate limits
- **Network Issues**: Robust network error handling
- **Thundering Herd**: Jitter prevents contention
- **LangChain Best Practice**: Recommended retry approach

### Consequences
- **Positive**: Better error handling, reduced contention
- **Negative**: Additional dependency
- **Neutral**: Standard retry pattern

### Implementation
- Exponential backoff with jitter
- Specialized retry strategies per error type
- Rate limit handling with intelligent backoff

---

## ADR-009: Skip Completed Chapters Optimization

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for efficient pipeline resumption

### Decision
Optimize resume behavior to skip already-completed chapters.

### Rationale
- **Cost Savings**: Avoid redundant API calls
- **Performance**: Faster pipeline resumption
- **User Experience**: Better resume behavior
- **Efficiency**: Process only missing chapters

### Consequences
- **Positive**: Cost savings, performance improvement
- **Negative**: Additional complexity in resume logic
- **Neutral**: Standard optimization technique

### Implementation
- Check existing chapter files before processing
- Skip already-completed chapters
- Transparent logging of skipped chapters

---

## ADR-010: Langfuse Observability

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for production-grade monitoring and debugging

### Decision
Replace custom callback with Langfuse observability.

### Rationale
- **Production Ready**: Professional monitoring solution
- **Cost Tracking**: Detailed cost analytics
- **Debugging**: Trace debugging capabilities
- **LangChain Best Practice**: Recommended observability

### Consequences
- **Positive**: Professional monitoring, cost tracking
- **Negative**: Additional service dependency
- **Neutral**: Standard observability approach

### Implementation
- Langfuse integration for tracing
- Fallback to custom JSONL logging
- Performance analytics and debugging

---

## ADR-011: Comprehensive Test Suite

**Date**: 2024-12-19  
**Status**: Accepted  
**Context**: Need for quality assurance and regression prevention

### Decision
Add extensive test coverage for all new features.

### Rationale
- **Quality Assurance**: Ensure feature correctness
- **Regression Prevention**: Prevent breaking changes
- **Documentation**: Tests serve as documentation
- **Best Practice**: Standard software development practice

### Consequences
- **Positive**: Better code quality, easier maintenance
- **Negative**: Additional development time
- **Neutral**: Standard development practice

### Implementation
- Unit tests for utility modules
- Integration tests for chain behavior
- Model tests for Pydantic validation
- Graph tests for node behavior

---

## Decision Summary

| ADR | Decision | Status | Impact |
|-----|----------|--------|---------|
| 001 | LangChain Framework | ✅ Accepted | Foundation |
| 002 | Multi-Provider LLM | ✅ Accepted | Reliability |
| 003 | Two-Layer Persistence | ✅ Accepted | Data Safety |
| 004 | Structured Outputs | ✅ Accepted | Type Safety |
| 005 | LLM Caching | ✅ Accepted | Cost Optimization |
| 006 | Fallback Models | ✅ Accepted | Resilience |
| 007 | Token Management | ✅ Accepted | Error Prevention |
| 008 | Advanced Retries | ✅ Accepted | Robustness |
| 009 | Skip Completed | ✅ Accepted | Efficiency |
| 010 | Langfuse Observability | ✅ Accepted | Monitoring |
| 011 | Test Suite | ✅ Accepted | Quality |

## ADR-012: Validation System Overhaul

**Date**: 2025-01-02  
**Status**: Accepted  
**Context**: Need for comprehensive quality assurance with proper error handling

### Decision
Overhaul validation system with comprehensive LangChain prompts and update to Claude 4.5 models.

### Rationale
- **Comprehensive Prompts**: Replace minimal prompts with detailed LangChain system/user prompts
- **Proper Error Handling**: Pipeline fails when QA errors occur (no silent failures)
- **Latest Models**: Use Claude 4.5 models for improved intelligence
- **Enhanced Scoring**: Add comprehensive scoring fields for better validation

### Consequences
- **Positive**: Better validation quality, proper error handling, latest model capabilities
- **Negative**: More complex prompts, potential for longer processing times
- **Neutral**: Standard approach for production-quality validation

### Implementation
- Replaced minimal checker prompt with comprehensive LangChain system prompt (100+ lines)
- Updated writer prompt with detailed formatting preservation requirements
- Fixed error handling to properly fail pipeline when QA errors occur
- Enhanced QAReport and CheckerOutput with comprehensive scoring fields
- Updated to Claude 4.5 models: `claude-sonnet-4-5-20250929` (primary), `claude-haiku-4-5-20251001` (fallback)
- Added "critical" severity level for QAIssue model
- Implemented proper ChatPromptTemplate structure for system/user messages

---

## Decision Summary

| ADR | Decision | Status | Impact |
|-----|----------|--------|---------|
| 001 | LangChain Framework | ✅ Accepted | Foundation |
| 002 | Multi-Provider LLM | ✅ Accepted | Reliability |
| 003 | Two-Layer Persistence | ✅ Accepted | Data Safety |
| 004 | Structured Outputs | ✅ Accepted | Type Safety |
| 005 | LLM Caching | ✅ Accepted | Cost Optimization |
| 006 | Fallback Models | ✅ Accepted | Resilience |
| 007 | Token Management | ✅ Accepted | Error Prevention |
| 008 | Advanced Retries | ✅ Accepted | Robustness |
| 009 | Skip Completed | ✅ Accepted | Efficiency |
| 010 | Langfuse Observability | ✅ Accepted | Monitoring |
| 011 | Test Suite | ✅ Accepted | Quality |
| 012 | Validation Overhaul | ✅ Accepted | Quality Assurance |

## Next Steps

1. **Performance Benchmarking**: Measure impact of optimizations
2. **Cost Analytics**: Track cost savings from caching
3. **Error Monitoring**: Monitor error rates and types
4. **User Feedback**: Gather feedback on resume behavior
5. **Documentation**: Update user documentation
6. **Validation Testing**: Test comprehensive validation with real content

---

*Last Updated: 2025-01-02*
*Version: 1.1.0*
