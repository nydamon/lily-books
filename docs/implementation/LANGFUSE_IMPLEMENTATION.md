# Langfuse Observability Implementation

## Overview

Lily Books now features comprehensive **Langfuse observability** integrated throughout the entire pipeline. This implementation follows Langfuse best practices to provide deep insights into LLM operations, costs, performance, and quality metrics.

## What is Langfuse?

[Langfuse](https://langfuse.com) is an open-source LLM engineering platform that provides:
- **Observability & Tracing**: Track every LLM interaction with full context
- **Cost Tracking**: Monitor token usage and costs across models
- **Quality Monitoring**: Track success rates, latencies, and user feedback
- **Debugging**: Drill down into specific traces to understand failures
- **Analytics**: Visualize trends over time with custom dashboards

## Setup

### 1. Get Langfuse Credentials

1. Sign up at [https://cloud.langfuse.com](https://cloud.langfuse.com) (free tier available)
2. Create a new project
3. Copy your **Public Key** and **Secret Key** from the project settings

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Langfuse Observability & Tracing
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Verify Installation

```bash
# Check if langfuse package is installed
poetry show langfuse

# Run a test pipeline
poetry run python -m lily_books run --slug test-book --book-id 11
```

## Architecture

### Tracing Hierarchy

```
📊 Trace (Session)
  └─ Pipeline Run: alice-wonderland
     ├─ 🔹 Span: ingest
     │   └─ Generation: IngestChain
     ├─ 🔹 Span: chapterize
     │   └─ Generation: ChapterizeChain
     ├─ 🔹 Span: rewrite
     │   ├─ Generation: writer_async_ch1
     │   ├─ Generation: writer_async_ch2
     │   └─ Generation: writer_async_ch3
     ├─ 🔹 Span: qa_text
     │   ├─ Generation: checker_async_ch1
     │   ├─ Generation: checker_async_ch2
     │   └─ Generation: checker_async_ch3
     └─ 🔹 Span: epub
         └─ Metadata: epub_generation
```

### Key Components

#### 1. **Session-Level Tracing** (`runner.py`)

Every pipeline run creates a **trace** (session) that captures:
- Book slug and ID
- Requested chapters
- Execution mode (sync/async)
- Runtime duration
- Success/failure status
- Error context

#### 2. **Node-Level Spans** (`runner.py`)

Each graph node operation creates a **span**:
- `ingest` - Fetching book text from Project Gutenberg
- `chapterize` - Splitting into chapters
- `rewrite` - Modernizing text with GPT-4o-mini
- `qa_text` - Quality checking with Claude Haiku
- `epub` - Building final EPUB

#### 3. **LLM Generation Tracking** (`llm_factory.py`)

All LLM calls automatically tracked via Langfuse callback:
- Input prompts
- Generated outputs
- Token usage (prompt, completion, total)
- Model names
- Temperature and parameters
- Latency
- Costs (auto-calculated)

#### 4. **Error Tracking** (`runner.py`)

Failures are captured with full context:
- Exception type and message
- Failed node
- Chapter numbers
- Input context
- Stack traces (in debug mode)

## What Gets Tracked?

### 📊 Automatic Tracking

- **All LLM Calls**: Every interaction with OpenRouter models
- **Token Counts**: Prompt, completion, and total tokens
- **Costs**: Automatic cost calculation per model
- **Latencies**: Time spent in each operation
- **Model Fallbacks**: When fallback models are used
- **Retries**: Self-healing retry attempts

### 🏷️ Metadata Tracked

Per trace:
```json
{
  "slug": "alice-wonderland",
  "book_id": 11,
  "mode": "async",
  "parallel": true,
  "chapters": [1, 2, 3],
  "chapter_count": 3
}
```

Per span:
```json
{
  "node": "rewrite",
  "chapter_count": 3,
  "duration_sec": 45.2
}
```

Per generation:
```json
{
  "model": "openai/gpt-4o-mini",
  "provider": "openrouter",
  "chapter": 1,
  "trace_name": "writer_async_ch1_alice-wonderland"
}
```

### 🏷️ Tags

Every trace is tagged with:
- `pipeline`
- `book-modernization`
- `{slug}` (book identifier)

## Viewing Traces

### Langfuse Dashboard

1. Navigate to [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Select your project
3. View **Traces** tab for session-level overview
4. Click into any trace to see detailed spans and generations
5. Use **Filter** to find specific books, chapters, or error conditions

### Key Views

#### Traces View
- See all pipeline runs
- Filter by book slug, success/failure, date range
- View aggregate metrics (total cost, avg latency, success rate)

#### Single Trace View
- Drill down into specific run
- See waterfall timeline of all operations
- Inspect LLM inputs/outputs
- Review error context
- Check token usage per operation

#### Analytics Dashboard
- Costs over time
- Token usage trends
- Success rates by node
- Latency percentiles (P50, P95, P99)
- Model usage distribution

## Advanced Features

### Custom Dashboards

Create custom dashboards in Langfuse to track:
- Cost per book
- Average fidelity scores by chapter
- Retry rates
- Specific error patterns

### Alerts

Set up alerts for:
- Cost thresholds exceeded
- High error rates
- Latency spikes
- Model fallback usage

### A/B Testing

Use Langfuse to compare:
- Different models (GPT-4o-mini vs GPT-4o)
- Temperature settings
- Prompt variations
- Batch sizes

## Best Practices

### 1. Session Management

Each pipeline run creates a unique session:
```python
with trace_pipeline(slug, book_id, chapters) as trace:
    # All operations inside are tracked under this session
    pass
```

### 2. Meaningful Trace Names

Use descriptive names for LLM operations:
```python
trace_name=f"writer_async_ch{chapter}_{slug}"
```

### 3. Error Context

Always provide context when tracking errors:
```python
track_error(trace, exception, {
    "node": "rewrite",
    "chapter": 1,
    "slug": slug
})
```

### 4. Flush Events

Ensure events are sent at critical points:
```python
flush_langfuse()  # At end of pipeline
```

### 5. Resource Management

Langfuse tracing is **lightweight** but be mindful:
- Events are batched automatically
- Flushing happens at pipeline end
- Context managers handle cleanup

## Performance Impact

Langfuse tracing adds **minimal overhead**:
- ~1-5ms per LLM call
- Async event submission (non-blocking)
- Automatic batching reduces network calls
- No impact on LLM latency

## Troubleshooting

### Traces Not Appearing

1. Check environment variables are set
2. Verify API keys are correct
3. Check network connectivity to Langfuse cloud
4. Look for errors in logs: `grep -i langfuse pipeline.log`

### Missing Generations

1. Ensure LLM factory is using `create_openai_llm_with_fallback`
2. Check callbacks are being passed to chains
3. Verify Langfuse initialization succeeded

### Disable Tracing

To temporarily disable:
```bash
LANGFUSE_ENABLED=false
```

Or in code:
```python
from lily_books.utils.langfuse_tracer import is_langfuse_enabled

if is_langfuse_enabled():
    # Tracing code
    pass
```

## Cost Tracking

Langfuse automatically calculates costs for:
- OpenAI models via OpenRouter
- Anthropic models via OpenRouter
- Token usage × model pricing

View costs:
- Per trace
- Per model
- Per time period
- Aggregated by tag

## Integration with Existing Logging

Langfuse **complements** existing logging:
- Regular logs: Local file-based debugging
- Langfuse traces: Structured observability with context

Both run simultaneously without conflict.

## Security & Privacy

### Data Handling

Langfuse traces contain:
- ✅ Metadata (book IDs, chapter numbers, metrics)
- ✅ LLM inputs/outputs (truncated to 1000 chars)
- ❌ No credentials or sensitive keys
- ❌ No full book content (only samples)

### Self-Hosting

For additional privacy, you can [self-host Langfuse](https://langfuse.com/docs/deployment/self-host):

```bash
# Update .env
LANGFUSE_HOST=https://your-langfuse-instance.com
```

## Roadmap

Future enhancements:
- [ ] Custom scores for fidelity ratings
- [ ] Evaluation datasets for regression testing
- [ ] Prompt versioning and management
- [ ] User feedback collection
- [ ] Automated quality regression alerts

## Resources

- **Langfuse Docs**: https://langfuse.com/docs
- **API Reference**: https://langfuse.com/docs/api
- **Best Practices**: https://langfuse.com/docs/observability/best-practices
- **GitHub**: https://github.com/langfuse/langfuse

## Support

For issues with Langfuse integration:
1. Check logs: `tail -f pipeline.log | grep -i langfuse`
2. Review traces in Langfuse dashboard
3. Consult this documentation
4. Reach out to Langfuse support: https://langfuse.com/support

---

**Implementation Date**: October 21, 2025  
**Langfuse Version**: 2.0.0+  
**Status**: ✅ Production Ready

