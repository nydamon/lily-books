# LLM Chains Agent

**Command**: `/llm-chains`

## Purpose

Expert in LangChain best practices, LLM orchestration, cost optimization, and observability for the Lily Books text modernization pipeline.

## Key Knowledge Areas

### 1. Writer Chain - Text Modernization ([src/lily_books/chains/writer.py](../../src/lily_books/chains/writer.py))

**Model**: GPT-4o-mini via OpenRouter
**Purpose**: Modernize 19th-century text to contemporary English

**Key Components**:
- **Prompt Template** ([writer.py:82-91](../../src/lily_books/chains/writer.py#L82-L91)):
  ```python
  WRITER_SYSTEM = """Modernize classic text to contemporary English while preserving meaning, dialogue, and structure. Convert _italics_ to <em>italics</em>. Target grade level 7-9. Never add modern concepts."""
  ```

- **Structured Output** ([writer.py:99](../../src/lily_books/chains/writer.py#L99)):
  - Uses `PydanticOutputParser` with `WriterOutput` schema
  - Ensures type-safe responses
  - Auto-validation of LLM output

- **Chain Construction** ([writer.py:161-173](../../src/lily_books/chains/writer.py#L161-L173)):
  ```python
  chain = (
      {"joined": ..., "format_instructions": ...}
      | writer_prompt
      | writer_llm
      | clean_llm_output  # Strip markdown
      | writer_parser  # Pydantic validation
  )
  ```

- **Adaptive Batching** ([writer.py:28](../../src/lily_books/chains/writer.py#L28)):
  - `calculate_optimal_batch_size()` targets 20% context utilization
  - Prevents context overflow
  - Maximizes throughput

- **Fallback Configuration** ([writer.py:137-147](../../src/lily_books/chains/writer.py#L137-L147)):
  - Primary: `openai/gpt-4o-mini`
  - Fallback: `openai/gpt-4o`
  - Temperature: 0.2 (creative but stable)
  - Timeout: 30s, Max retries: 2

---

### 2. Checker Chain - QA Validation ([src/lily_books/chains/checker.py](../../src/lily_books/chains/checker.py))

**Model**: Claude 4.5 Haiku via OpenRouter
**Purpose**: Validate text quality with comprehensive QA report

**Key Components**:
- **Comprehensive QA Report** ([checker.py:75-134](../../src/lily_books/chains/checker.py#L75-L134)):
  - Fidelity score (0-100, target: ≥92)
  - Readability grade (Flesch-Kincaid, target: 7-9)
  - Formatting preservation (quotes, italics)
  - Modernization completeness
  - Tone consistency
  - Issue detection with severity levels

- **Graduated Quality Gates** ([checker.py:137-150](../../src/lily_books/chains/checker.py#L137-L150)):
  - Evaluates aggregate chapter quality
  - Flexible thresholds per book
  - Soft validation (continue on error)

- **Fallback Configuration** ([checker.py:94-104](../../src/lily_books/chains/checker.py#L94-L104)):
  - Primary: `anthropic/claude-haiku-4.5`
  - Fallback: `anthropic/claude-sonnet-4.5`
  - Temperature: 0.0 (deterministic)
  - Timeout: 30s, Max retries: 2

---

### 3. LLM Factory ([src/lily_books/utils/llm_factory.py](../../src/lily_books/utils/llm_factory.py))

**Purpose**: Unified LLM creation with fallback configuration

**Key Features**:
- **OpenRouter-Only Architecture**: Single API for all LLMs
- **Provider Selection**: `openai`, `anthropic`
- **RunnableWithFallbacks Pattern**: Auto-fallback on primary model failure
- **Cache Integration**: Optional LLM caching
- **Consistent Configuration**: Temperature, timeout, max_retries

**Usage**:
```python
llm = create_llm_with_fallback(
    provider="openai",
    temperature=0.2,
    timeout=30,
    max_retries=2,
    cache_enabled=True
)
```

---

### 4. Token Management ([src/lily_books/utils/tokens.py](../../src/lily_books/utils/tokens.py))

**Purpose**: Token counting, context validation, adaptive batching

**Key Functions**:

**Token Counting**:
```python
token_count = count_tokens(text, model="openai/gpt-4o-mini")
```
- Uses `tiktoken` for accurate counting
- Model-specific encodings
- Prevents context overflow

**Context Window Validation**:
```python
validate_context_window(text, model, safety_margin=0.2)
```
- Checks text fits in model's context window
- 20% safety margin
- Raises error if exceeds

**Adaptive Batch Sizing**:
```python
batch_size = calculate_optimal_batch_size(
    paragraphs,
    model="openai/gpt-4o-mini",
    target_utilization=0.2,
    min_batch_size=1,
    max_batch_size=10
)
```
- Targets 20% context utilization
- Balances throughput and safety
- Adapts to paragraph length

**Token Usage Logging**:
```python
log_token_usage(prompt_tokens, completion_tokens, model)
```
- Logs to console and Langfuse
- Calculates costs
- Tracks cumulative usage

---

### 5. Langfuse Observability ([src/lily_books/observability.py](../../src/lily_books/observability.py))

**Purpose**: Production-grade LLM tracing and monitoring

**What Gets Tracked**:
- ✅ All LLM calls (prompt, completion, model)
- ✅ Token usage (prompt, completion, total)
- ✅ Costs (automatic per model)
- ✅ Latencies (end-to-end timing)
- ✅ Errors (full context with trace URLs)
- ✅ Quality metrics (fidelity scores, readability)
- ✅ Debug events (step-by-step execution)

**Integration**:
```python
callback = create_observability_callback(slug)
llm = create_llm_with_fallback(..., callbacks=[callback])
```

**Trace URLs**: Every error includes clickable Langfuse trace URL for debugging

**Documentation**: [docs/implementation/LANGFUSE_IMPLEMENTATION.md](../../docs/implementation/LANGFUSE_IMPLEMENTATION.md)

---

### 6. LLM Response Caching

**Purpose**: 30-50% cost reduction on repeated operations

**How It Works**:
- Semantic caching via LangChain
- TTL: 3600 seconds (1 hour)
- Cache key: Hash of prompt + model
- Enabled by default in production

**Cache Hit Scenarios**:
- Rerunning QA validation
- Remediation retries
- Pipeline restarts after failures

**Configuration**:
```bash
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
CACHE_TYPE=memory
```

---

## Key Files

- [src/lily_books/chains/writer.py](../../src/lily_books/chains/writer.py) - Text modernization (GPT-4o-mini)
- [src/lily_books/chains/checker.py](../../src/lily_books/chains/checker.py) - QA validation (Claude Haiku)
- [src/lily_books/utils/llm_factory.py](../../src/lily_books/utils/llm_factory.py) - LLM creation with fallbacks
- [src/lily_books/utils/tokens.py](../../src/lily_books/utils/tokens.py) - Token management
- [src/lily_books/observability.py](../../src/lily_books/observability.py) - Langfuse tracing
- [src/lily_books/utils/validators.py](../../src/lily_books/utils/validators.py) - Output validation
- [src/lily_books/config.py](../../src/lily_books/config.py) - Model configuration
- [docs/implementation/LANGFUSE_IMPLEMENTATION.md](../../docs/implementation/LANGFUSE_IMPLEMENTATION.md) - Observability setup

---

## Common Questions

### Q: How do I optimize token usage and reduce costs?

**Answer**:

1. **Enable Caching** (30-50% savings):
   ```bash
   CACHE_ENABLED=true
   ```

2. **Adaptive Batching**:
   - Writer chain auto-calculates optimal batch size
   - Targets 20% context utilization
   - Prevents overflow while maximizing throughput

3. **Skip Completed Work**:
   - Pipeline checks for existing chapter docs
   - Skips rewrite/QA for completed chapters
   - Saves costs on restarts

4. **Monitor with Langfuse**:
   - Track token usage per book
   - Identify cost hotspots
   - Optimize prompts based on data

**Cost Breakdown** (per 100k word book):
- Modernization: $2.50-5.50 (GPT-4o-mini)
- QA Validation: $0.50-2.00 (Claude Haiku)
- **Total**: $3.00-7.50 per book

---

### Q: Why is caching not working?

**Answer**:

Check these common issues:

1. **Cache disabled in config**:
   ```bash
   # .env
   CACHE_ENABLED=true
   ```

2. **Prompts changing between runs**:
   - Cache key includes prompt hash
   - Even small prompt changes invalidate cache
   - Use consistent prompts for cache hits

3. **TTL expired**:
   ```bash
   CACHE_TTL_SECONDS=3600  # 1 hour default
   ```

4. **Different models**:
   - Cache key includes model name
   - Changing models invalidates cache

**Debug**: Check Langfuse traces for cache hit/miss indicators

---

### Q: How do I add a new LLM provider?

**Answer**:

1. **Add to llm_factory.py**:
   ```python
   if provider == "new_provider":
       primary_llm = ChatNewProvider(
           model=settings.new_provider_model,
           temperature=temperature,
           timeout=timeout,
           max_retries=max_retries
       )
   ```

2. **Add configuration**:
   ```bash
   # .env
   NEW_PROVIDER_MODEL=new_provider/model-name
   NEW_PROVIDER_FALLBACK_MODEL=new_provider/fallback-model
   ```

3. **Update settings.py**:
   ```python
   new_provider_model: str = Field(default="new_provider/model-name")
   new_provider_fallback_model: str = Field(default="new_provider/fallback")
   ```

4. **Add to chains**:
   ```python
   # writer.py or checker.py
   llm = create_llm_with_fallback(provider="new_provider", ...)
   ```

---

### Q: How do I debug LLM failures?

**Answer**:

1. **Check Langfuse Trace**:
   - Every error includes trace URL
   - Click URL to see exact inputs that caused failure
   - View token usage, timing, error details

2. **Review Structured Output Validation**:
   - Pydantic validation errors show in logs
   - Check if LLM output matches schema
   - Use `safe_parse_*_output()` functions

3. **Inspect Retry Logic**:
   - Check if fallback model was used
   - Review retry count in logs
   - Examine enhanced prompts from retry

4. **Test with Single Chapter**:
   ```bash
   python -m lily_books run 11 --slug test --chapters 1
   ```

5. **Enable Debug Logging**:
   ```bash
   LOG_LEVEL=DEBUG
   ```

---

### Q: How does the fallback model system work?

**Answer**:

**RunnableWithFallbacks Pattern**:

```python
primary_llm = ChatOpenAI(model="openai/gpt-4o-mini")
fallback_llm = ChatOpenAI(model="openai/gpt-4o")

llm_with_fallback = primary_llm.with_fallbacks([fallback_llm])
```

**Fallback Triggers**:
- API errors (rate limits, timeouts)
- Malformed responses
- Context length exceeded
- Server errors (500, 503)

**NOT Triggered By**:
- Invalid API keys (fails immediately)
- Quota exceeded (fails immediately)
- Invalid model names

**Monitoring**:
- Langfuse shows which model executed
- Logs indicate fallback usage
- Cost tracking per model

---

### Q: How do I adjust batch sizing?

**Answer**:

**Automatic (Recommended)**:
```python
# writer.py already handles this
batch_size = calculate_optimal_batch_size(
    paragraphs,
    model=settings.openai_model,
    target_utilization=0.2,  # 20% of context
    min_batch_size=1,
    max_batch_size=10
)
```

**Manual Override**:
```python
# config.py
class Settings(BaseSettings):
    max_batch_size: int = Field(default=10, description="Max paragraphs per batch")
    target_utilization: float = Field(default=0.2, description="Target context %")
```

**Considerations**:
- Larger batches = fewer API calls = lower cost
- Smaller batches = less context overflow risk
- Default 20% utilization is conservative but safe

---

### Q: How do I customize the Writer or Checker prompts?

**Answer**:

**Writer System Prompt** ([writer.py:82-85](../../src/lily_books/chains/writer.py#L82-L85)):
```python
WRITER_SYSTEM = """Modernize classic text to contemporary English while preserving meaning, dialogue, and structure. Convert _italics_ to <em>italics</em>. Target grade level 7-9. Never add modern concepts."""
```

**Checker System Prompt** (in checker.py):
```python
CHECKER_SYSTEM = """You are a literary QA expert..."""
```

**Best Practices**:
- Keep prompts concise (reduces token usage)
- Be explicit about output format
- Include examples for complex tasks
- Test with single chapter first
- Monitor fidelity scores after changes

---

## Best Practices

### 1. Always Use Structured Outputs
- Pydantic schemas ensure type safety
- Automatic validation catches malformed responses
- Better error messages

### 2. Enable Langfuse in Production
- Essential for debugging
- Cost tracking per book
- Performance optimization insights

### 3. Monitor Token Usage
- Log token counts with `log_token_usage()`
- Track cumulative costs
- Optimize prompts based on data

### 4. Use Adaptive Batching
- Let `calculate_optimal_batch_size()` handle it
- Don't hardcode batch sizes
- Prevents context overflow

### 5. Test Prompts with Real Data
- Use actual 19th-century text
- Validate output quality
- Check token efficiency

### 6. Handle Fallbacks Gracefully
- Log when fallback model is used
- Monitor cost implications
- Ensure both models produce valid output

---

## Related Agents

- [/langgraph-pipeline](langgraph-pipeline.md) - For integrating LLM chains into nodes
- [/qa-validation](qa-validation.md) - For quality metrics and validation
- [/testing](testing.md) - For testing LLM chains

---

**Last Updated**: 2025-10-25
**Version**: 1.0
