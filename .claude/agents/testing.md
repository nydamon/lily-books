# Testing & Reliability Agent

**Command**: `/testing`

## Purpose

Expert in testing, error handling, and resilience patterns for the Lily Books pipeline.

## Key Knowledge Areas

### 1. Test Suite Structure

**Location**: [tests/](../../tests/)

**Test Files** (51 Python files):
- `test_basic.py` - Basic sanity tests
- `test_chains.py` - Writer/Checker chain tests
- `test_graph_nodes.py` - Graph node behavior
- `test_models.py` - Pydantic model validation
- `test_tools.py` - Tool functionality
- `test_full_pipeline.py` - End-to-end pipeline
- `test_async_pipeline.py` - Async processing
- `test_publishing.py` - Publishing workflow
- `test_agents.py` - Agent slash commands (NEW)

### 2. Testing Patterns

**Mock LLM Calls**:
```python
from unittest.mock import Mock, patch

@patch('lily_books.chains.writer.create_llm_with_fallback')
def test_rewrite_chapter(mock_llm):
    mock_llm.return_value.invoke.return_value = {
        "paragraphs": [{"modern": "Modernized text"}]
    }
    # Test code
```

**Fixtures** ([tests/conftest.py](../../tests/conftest.py)):
```python
@pytest.fixture
def sample_chapter():
    return ChapterSplit(
        chapter=1,
        title="Test Chapter",
        paragraphs=["Original text"]
    )
```

### 3. Error Handling ([models.py:8-88](../../src/lily_books/models.py#L8-L88))

**PipelineError Hierarchy**:
```python
class PipelineError(Exception):
    def __init__(self, message, slug, node, context=None):
        self.slug = slug
        self.node = node
        self.context = context or {}
```

**Subclasses**:
- IngestError - Book ingestion failures
- ChapterizeError - Chapter splitting failures
- RewriteError - Text modernization failures
- QAError - QA validation failures
- EPUBError - EPUB generation failures
- TTSError - TTS generation failures
- MasterError - Audio mastering failures
- PackageError - Final packaging failures
- CoverError - Cover generation failures
- PublishingError - Publishing/distribution failures

### 4. Retry Logic ([utils/retry.py](../../src/lily_books/utils/retry.py))

**Tenacity-Based Retries**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def api_call():
    # Retries with exponential backoff: 4s, 8s, 10s
```

**Features**:
- Exponential backoff
- Jitter (prevent thundering herd)
- Max attempts
- Specialized strategies per error type

### 5. Circuit Breaker ([utils/circuit_breaker.py](../../src/lily_books/utils/circuit_breaker.py))

**Purpose**: Prevent cascading failures

**States**:
- **CLOSED**: Normal operation
- **OPEN**: Too many failures, block requests
- **HALF_OPEN**: Test if service recovered

**Configuration**:
```python
circuit_breaker = CircuitBreaker(
    failure_threshold=5,  # Open after 5 failures
    timeout=60  # Try again after 60s
)
```

### 6. Self-Healing ([utils/fail_fast.py](../../src/lily_books/utils/fail_fast.py))

**Fail Fast on Critical Errors**:
```python
@fail_fast_on_exception
def critical_operation():
    # Raises immediately on auth errors, quota exceeded
    # Retries on transient errors
```

**LLM Response Checking**:
```python
response = check_llm_response(llm_output)
# Validates non-empty, structured correctly
```

### 7. Observability ([utils/debug_logger.py](../../src/lily_books/utils/debug_logger.py))

**Debug Events**:
```python
log_step("node_name.action", key="value")
update_activity("Processing chapter 3")
```

**Async Function Tracing**:
```python
@debug_async_function
async def my_async_node(state):
    # Auto-logged start/end/errors
```

## Key Files

- [tests/](../../tests/) - Full test suite (51 files)
- [src/lily_books/utils/circuit_breaker.py](../../src/lily_books/utils/circuit_breaker.py) - Circuit breaker
- [src/lily_books/utils/retry.py](../../src/lily_books/utils/retry.py) - Retry logic
- [src/lily_books/utils/fail_fast.py](../../src/lily_books/utils/fail_fast.py) - Self-healing
- [src/lily_books/models.py](../../src/lily_books/models.py) - Error models
- [src/lily_books/utils/debug_logger.py](../../src/lily_books/utils/debug_logger.py) - Debug logging

## Common Questions

### Q: How do I write tests for a new feature?

**Answer**:

1. **Create test file**:
```python
# tests/test_my_feature.py
import pytest
from lily_books.my_module import my_function

class TestMyFeature:
    def test_basic_functionality(self):
        result = my_function("input")
        assert result == "expected"
```

2. **Mock LLM calls**:
```python
from unittest.mock import Mock, patch

@patch('lily_books.utils.llm_factory.create_llm_with_fallback')
def test_with_llm(mock_llm):
    mock_llm.return_value.invoke.return_value = {"output": "data"}
    # Test code
```

3. **Use fixtures**:
```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

4. **Run tests**:
```bash
poetry run pytest tests/test_my_feature.py -v
```

### Q: How do I debug test failures?

**Answer**:

1. **Run with verbose output**:
```bash
poetry run pytest tests/test_file.py::test_name -vv
```

2. **Use pytest debugging**:
```bash
poetry run pytest tests/test_file.py::test_name --pdb
```

3. **Check Langfuse traces** (for integration tests):
```python
# Trace URL in logs
TRACE_LINK pipeline_sync_test-slug: https://cloud.langfuse.com/trace/...
```

4. **Enable debug logging**:
```bash
LOG_LEVEL=DEBUG poetry run pytest tests/test_file.py
```

### Q: How do circuit breakers work?

**Answer**:

**Normal Flow (CLOSED)**:
```python
circuit = CircuitBreaker(failure_threshold=5, timeout=60)

try:
    result = circuit.call(api_function)
    # Success - circuit stays CLOSED
except CircuitBreakerOpen:
    # Too many failures - circuit OPEN
    # Requests blocked for 60s
```

**States**:
1. **CLOSED**: All requests pass through
2. **OPEN**: Requests blocked after 5 failures
3. **HALF_OPEN**: After 60s, test one request
   - Success → CLOSED
   - Failure → OPEN for another 60s

**Use Cases**:
- Prevent hammering failed API
- Graceful degradation
- Service recovery detection

### Q: How does retry logic work?

**Answer**:

**Basic Retry**:
```python
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def flaky_function():
    # Retries up to 3 times
```

**Exponential Backoff**:
```python
from tenacity import retry, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def api_call():
    # Waits: 4s, 8s, 10s (capped at max)
```

**Conditional Retry**:
```python
from tenacity import retry, retry_if_exception_type

@retry(retry=retry_if_exception_type(RateLimitError))
def api_with_rate_limit():
    # Only retries on RateLimitError
```

**In Lily Books**:
- Writer chain: 2 retries with exponential backoff
- Checker chain: 2 retries
- API calls: 3 retries with jitter

### Q: How do I test error handling?

**Answer**:

**Test Expected Errors**:
```python
import pytest
from lily_books.models import RewriteError

def test_error_raised():
    with pytest.raises(RewriteError) as exc_info:
        my_function_that_should_fail()

    assert exc_info.value.slug == "test-slug"
    assert exc_info.value.node == "rewrite"
```

**Test Error Context**:
```python
def test_error_context():
    try:
        failing_function()
    except PipelineError as e:
        assert e.context["chapter"] == 1
        assert "details" in e.context
```

**Mock Failures**:
```python
from unittest.mock import Mock, patch

@patch('lily_books.api.external_api')
def test_api_failure(mock_api):
    mock_api.side_effect = ConnectionError("API down")

    with pytest.raises(IngestError):
        ingest_book(book_id=123)
```

## Best Practices

### 1. Test Happy Path First
- Ensure basic functionality works
- Then add edge cases and error tests

### 2. Mock External Dependencies
- LLM calls
- API requests
- File I/O (when not integration testing)

### 3. Use Fixtures for Common Data
- Sample chapters
- Test configurations
- Mock responses

### 4. Test Error Paths
- Invalid inputs
- API failures
- LLM response malformation

### 5. Integration Tests with Real Data
- Test with actual Gutenberg books
- Validate end-to-end pipeline
- Use `--chapters 1` for speed

### 6. Monitor with Langfuse
- Track test execution traces
- Debug flaky tests
- Measure test coverage of LLM calls

## Related Agents

- [/langgraph-pipeline](langgraph-pipeline.md) - For pipeline testing
- [/llm-chains](llm-chains.md) - For chain testing
- [/qa-validation](qa-validation.md) - For QA testing

---

**Last Updated**: 2025-10-25
**Version**: 1.0
