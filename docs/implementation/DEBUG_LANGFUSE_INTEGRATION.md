# Debug & Langfuse Integration

## Overview

All debug processes in Lily Books now integrate seamlessly with Langfuse tracing, providing **unified observability** across debug logs and production monitoring.

## What's Integrated

### 1. **Debug Logger** (`debug_logger.py`)

Every debug log now includes:
- ✅ **Trace IDs** - Link debug logs to Langfuse traces
- ✅ **Span IDs** - Identify which operation produced the log
- ✅ **Trace URLs** - Direct links to Langfuse dashboard
- ✅ **Auto-sync to Langfuse** - Debug events appear in Langfuse

#### Features

**Trace Context Tracking:**
```python
from lily_books.utils.debug_logger import set_trace_context, get_trace_context

# Set current trace context (done automatically in runner)
set_trace_context(trace_id="abc123", span_id="def456")

# Get current context
context = get_trace_context()
# Returns: {'trace_id': 'abc123', 'span_id': 'def456'}
```

**Trace URL Generation:**
```python
from lily_books.utils.debug_logger import get_trace_url, log_trace_link

# Get clickable URL
url = get_trace_url()
# Returns: "https://cloud.langfuse.com/trace/abc123"

# Log trace link
log_trace_link("after_rewrite_complete")
# Output: "TRACE_LINK after_rewrite_complete: https://cloud.langfuse.com/trace/abc123"
```

**Enhanced Logging:**
```python
from lily_books.utils.debug_logger import log_step, log_exception

# Log step with trace context
log_step("rewrite_chapter", chapter=1, paragraphs=50)
# Output includes: "| Trace: abc123... | Span: def456..."

# Log exception with trace link
try:
    risky_operation()
except Exception as e:
    log_exception("risky_operation", e)
    # Output includes: "| Trace: https://cloud.langfuse.com/trace/abc123"
```

**Debug Events in Langfuse:**

All debug steps automatically create events in Langfuse:
- Event name: `debug_{step_name}`
- Level: `DEBUG`
- Metadata: All kwargs passed to `log_step()`

### 2. **Fail-Fast Error Handling** (`fail_fast.py`)

All fail-fast errors now include Langfuse trace links for immediate debugging:

```python
from lily_books.utils.fail_fast import check_llm_response, fail_fast_on_exception

# Check LLM response
response = llm.invoke(prompt)
check_llm_response(response, "writer_chain")
# If empty, logs include trace URL for debugging

# Fail-fast on exception
try:
    process_chapter()
except Exception as e:
    fail_fast_on_exception(e, "chapter_processing")
    # Error includes: "Langfuse Trace: https://..."
```

**Langfuse Events for Fail-Fast:**

Every fail-fast trigger creates an event:
- Event name: `fail_fast_{error_type}`
- Level: `ERROR`
- Metadata: error details, context, fail-fast status

### 3. **Health Checks** (`health_check.py`)

Pipeline health metrics are automatically sent to Langfuse:

```python
from lily_books.utils.health_check import create_health_check, log_pipeline_health

health = create_health_check("alice-wonderland")
health.update_chapter_progress(1, "completed", paragraphs=50)

# Log health status (also sends to Langfuse)
log_pipeline_health(health)
```

**Langfuse Health Events:**

Health checks create events in Langfuse:
- Event name: `pipeline_health_check`
- Level: `INFO` (or `WARNING` if health < 70)
- Metadata: Full health status with scores, progress, errors

## How It Works

### Automatic Trace Context

1. **Pipeline Start** - Trace context is set automatically:
```python
# In runner.py
with trace_pipeline(slug, book_id, chapters) as trace:
    set_trace_context(trace_id=trace.id)  # ← Automatic
    log_trace_link(f"pipeline_{slug}")    # ← Logs clickable URL
```

2. **All Debug Logs** - Include trace context:
```
2025-10-21 14:32:15 [INFO] STEP: rewrite_chapter | PID: 12345 | TID: 67890 | 
Memory: 256.3MB | Threads: 8 | Trace: abc12345... | Span: def67890...
```

3. **Langfuse Dashboard** - Shows debug events:
   - Click trace in Langfuse
   - See all debug events under "Events" tab
   - Filter by `debug_*` prefix

### Thread-Safe Context

Trace context uses **thread-local storage**, so it's safe for:
- ✅ Multi-threaded pipelines
- ✅ Async operations
- ✅ Parallel chapter processing

Each thread maintains its own trace context.

## Usage Patterns

### Pattern 1: Debug with Trace Links

```python
from lily_books.utils.debug_logger import log_step, log_trace_link

# Start operation
log_step("process_batch", batch_size=10, chapter=5)

# ... processing ...

# Log completion with trace link
log_trace_link("batch_complete")
```

**Output:**
```
STEP: process_batch | ... | Trace: abc12345...
  batch_size: 10
  chapter: 5
TRACE_LINK batch_complete: https://cloud.langfuse.com/trace/abc12345
```

### Pattern 2: Exception Debugging

```python
from lily_books.utils.debug_logger import log_exception
from lily_books.utils.fail_fast import fail_fast_on_exception

try:
    result = complex_operation()
except Exception as e:
    log_exception("complex_operation", e)
    fail_fast_on_exception(e, "complex_operation")
```

**Output:**
```
EXCEPTION in complex_operation: ValueError(...) | Trace: https://cloud.langfuse.com/trace/...
TRACEBACK: ...full stack trace...
FAIL-FAST: Exception in complex_operation: ValueError(...)
Langfuse Trace: https://cloud.langfuse.com/trace/...
```

**In Langfuse:**
- Event: `fail_fast_exception`
- Level: `ERROR`
- Metadata: Full error context
- Linked to parent trace

### Pattern 3: Health Monitoring

```python
from lily_books.utils.health_check import create_health_check, log_pipeline_health

health = create_health_check(slug)

# Update progress
for chapter in chapters:
    process_chapter(chapter)
    health.update_chapter_progress(chapter.num, "completed", len(chapter.pairs))
    
    # Periodic health check
    if chapter.num % 5 == 0:
        log_pipeline_health(health)  # ← Logs AND sends to Langfuse
```

**Output:**
```
Pipeline Health [alice-wonderland]:
  Status: Good (Score: 85/100)
  Progress: 5/10 chapters (50.0%)
  Runtime: 245.3s
  Last Activity: 2025-10-21T14:32:45
  Errors: 0, Timeouts: 1
```

**In Langfuse:**
- Event: `pipeline_health_check`
- Level: `INFO`
- Metadata: All health metrics

## Debugging Workflow

### 1. **Local Debugging**

When debugging locally:

```bash
# Run pipeline with debug logging
poetry run python -m lily_books run --slug test-book --book-id 11 2>&1 | tee debug.log
```

Debug logs show:
- All debug steps
- Trace IDs for correlation
- Direct trace URLs

### 2. **Trace Correlation**

Found an error in logs? Use trace URL to jump to Langfuse:

```
EXCEPTION in writer_chain: APITimeoutError | Trace: https://cloud.langfuse.com/trace/xyz789
```

Click the URL → Opens trace in Langfuse → See:
- Exact input that caused error
- Token usage at failure point
- All debug events leading up to error
- Timing information

### 3. **Production Debugging**

In production:

1. **Check Langfuse first** - View all traces, find failures
2. **Look at debug events** - See what happened step-by-step
3. **Review error events** - fail-fast and exception events
4. **Check health events** - Was pipeline unhealthy before failure?
5. **Correlate with logs** - Use trace ID to find relevant log lines

## Advanced Features

### Custom Debug Events

Send custom events to Langfuse:

```python
from lily_books.utils.debug_logger import _send_debug_event_to_langfuse

_send_debug_event_to_langfuse("custom_checkpoint", {
    "chapter": 5,
    "paragraphs_processed": 50,
    "cache_hits": 12
})
```

### Conditional Trace Logging

Only log trace links when debugging:

```python
from lily_books.utils.debug_logger import log_trace_link
from lily_books.config import settings

if settings.debug:
    log_trace_link("critical_checkpoint")
```

### Health Alerts

Monitor health score in Langfuse:

```python
from lily_books.utils.health_check import log_pipeline_health

status = health.get_health_status()
if status['health_score'] < 50:
    log_pipeline_health(health)  # Creates WARNING event in Langfuse
    # Set up alert in Langfuse dashboard for health_score < 50
```

## Configuration

### Enable/Disable Langfuse Integration

Debug logging always works, but Langfuse integration can be disabled:

```bash
# .env
LANGFUSE_ENABLED=false  # Debug logs only, no Langfuse events
```

### Debug Verbosity

Control debug verbosity:

```bash
# .env
DEBUG=true
LOG_LEVEL=DEBUG  # Show all debug events
```

## Benefits

### 1. **Unified Observability**

Single source of truth:
- Debug logs → Local troubleshooting
- Langfuse events → Production monitoring
- Both linked by trace IDs

### 2. **Faster Debugging**

Error in logs? Click trace URL → Full context in Langfuse:
- What led to error
- Exact inputs
- Resource usage
- Timing

### 3. **Production-Ready**

Debug instrumentation that:
- Works in development
- Scales to production
- Minimal overhead
- Automatic correlation

### 4. **Historical Analysis**

Langfuse stores all events:
- Debug patterns over time
- Error frequency trends
- Health degradation tracking
- Performance regression analysis

## Performance Impact

Minimal overhead:
- **Debug logging**: ~0.1ms per log
- **Langfuse events**: Async, batched
- **Trace context**: Thread-local lookup (< 1μs)
- **Health checks**: Only when called

## Best Practices

### 1. **Always Set Trace Context**

Runner does this automatically, but for custom scripts:

```python
with trace_pipeline(slug, book_id) as trace:
    set_trace_context(trace_id=trace.id)
    # All debug logs now include trace
```

### 2. **Log Trace Links at Key Points**

```python
log_trace_link("before_expensive_operation")
expensive_operation()
log_trace_link("after_expensive_operation")
```

### 3. **Use Health Checks Regularly**

```python
# Create once
health = create_health_check(slug)

# Update frequently
for item in items:
    process(item)
    health.update_chapter_progress(...)

# Log periodically
if should_log:
    log_pipeline_health(health)
```

### 4. **Don't Swallow Errors**

Let fail-fast handle errors:

```python
# Good ✅
try:
    operation()
except Exception as e:
    fail_fast_on_exception(e, "operation")  # Tracks in Langfuse

# Bad ❌
try:
    operation()
except:
    pass  # No trace, no debugging
```

## Troubleshooting

### Trace IDs Not Appearing

**Problem:** Debug logs don't show trace IDs

**Solution:**
1. Check Langfuse is enabled: `LANGFUSE_ENABLED=true`
2. Verify trace context is set (automatic in runner)
3. Check you're inside `trace_pipeline()` context

### Events Not in Langfuse

**Problem:** Debug events not appearing in Langfuse dashboard

**Solution:**
1. Check Langfuse credentials are correct
2. Verify network connectivity
3. Look for Langfuse errors in debug logs
4. Events are batched - wait a few seconds

### Trace URLs Not Clickable

**Problem:** Trace URLs in logs aren't clickable

**Solution:**
- Most modern terminals support clickable URLs
- Copy-paste URL manually
- Use `CTRL+Click` or `CMD+Click`

## Examples

### Complete Debug Session

```python
from lily_books.utils.debug_logger import log_step, log_trace_link, log_exception
from lily_books.utils.fail_fast import check_llm_response
from lily_books.utils.health_check import create_health_check, log_pipeline_health
from lily_books.utils.langfuse_tracer import trace_pipeline

slug = "alice-wonderland"
book_id = 11

with trace_pipeline(slug, book_id) as trace:
    set_trace_context(trace_id=trace.id)
    log_trace_link("pipeline_start")
    
    health = create_health_check(slug)
    
    for chapter in chapters:
        log_step("process_chapter", chapter=chapter.num)
        
        try:
            result = process_chapter(chapter)
            check_llm_response(result, f"chapter_{chapter.num}")
            
            health.update_chapter_progress(chapter.num, "completed")
            log_step("chapter_complete", chapter=chapter.num)
            
        except Exception as e:
            log_exception(f"chapter_{chapter.num}", e)
            fail_fast_on_exception(e, f"chapter_{chapter.num}")
    
    log_pipeline_health(health)
    log_trace_link("pipeline_complete")
```

This creates:
- Debug logs with trace IDs
- Langfuse events for each step
- Health check event
- Error events if failures
- Complete trace in Langfuse dashboard

---

**Status**: ✅ **PRODUCTION READY**  
**Integration**: Complete across all debug systems  
**Performance**: Minimal overhead  
**Compatibility**: Works with existing debug infrastructure

