# LangGraph Pipeline Agent

**Command**: `/langgraph-pipeline`

## Purpose

Expert in the LangGraph state machine architecture, node orchestration, and pipeline flow control for the Lily Books modernization pipeline.

## Key Knowledge Areas

### 1. Graph Structure ([src/lily_books/graph.py](../../src/lily_books/graph.py))

The complete 1531-line state machine that orchestrates the entire pipeline:

**Core Nodes**:
- `ingest_node` ([graph.py:72-102](../../src/lily_books/graph.py#L72-L102)) - Load text from Gutendex API
- `chapterize_node` ([graph.py:104-146](../../src/lily_books/graph.py#L104-L146)) - Split into chapters
- `rewrite_node` ([graph.py:332-482](../../src/lily_books/graph.py#L332-L482)) - Modernize text
- `rewrite_node_async` ([graph.py:148-330](../../src/lily_books/graph.py#L148-L330)) - Parallel modernization

**QA Nodes** (optional via `ENABLE_QA_REVIEW`):
- `qa_text_node` ([graph.py:661-835](../../src/lily_books/graph.py#L661-L835)) - Quality validation
- `qa_text_node_async` ([graph.py:484-659](../../src/lily_books/graph.py#L484-L659)) - Parallel QA
- `remediate_node` ([graph.py:837-925](../../src/lily_books/graph.py#L837-L925)) - Fix failing chapters

**Publishing Nodes**:
- `metadata_node` ([graph.py:927-987](../../src/lily_books/graph.py#L927-L987)) - Generate metadata
- `cover_node` ([graph.py:989-1039](../../src/lily_books/graph.py#L989-L1039)) - Generate AI cover
- `epub_node` ([graph.py:1041-1106](../../src/lily_books/graph.py#L1041-L1106)) - Build EPUB

**Audio Nodes** (optional via `ENABLE_AUDIO`):
- `tts_node` ([graph.py:1108-1162](../../src/lily_books/graph.py#L1108-L1162)) - Text-to-speech
- `master_node` ([graph.py:1164-1230](../../src/lily_books/graph.py#L1164-L1230)) - Audio mastering
- `qa_audio_node` ([graph.py:1232-1293](../../src/lily_books/graph.py#L1232-L1293)) - Audio QA
- `package_node` ([graph.py:1295-1360](../../src/lily_books/graph.py#L1295-L1360)) - Package deliverables

**Distribution Nodes** (optional via `ENABLE_PUBLISHING`):
- `assign_identifiers_node` - Assign ASIN/ISBN/Google ID
- `prepare_editions_node` - Create Kindle + Universal editions
- `generate_retail_metadata_node` - SEO metadata
- `calculate_pricing_node` - Pricing optimization
- `validate_metadata_node` - Metadata validation
- `validate_epub_node` - EPUB validation
- `human_review_node` - Manual approval gate
- `upload_to_publishdrive_node` - **PRIMARY** PublishDrive upload
- `upload_to_kdp_node` - **LEGACY** Amazon KDP (backup)
- `upload_to_google_node` - **LEGACY** Google Play (backup)
- `upload_to_d2d_node` - **LEGACY** Draft2Digital (backup)
- `generate_publishing_report_node` - Final report

### 2. Conditional Routing

**QA Gate** ([graph.py:1416-1430](../../src/lily_books/graph.py#L1416-L1430)):
```python
def should_remediate(state: FlowState) -> str:
    return "remediate" if not state.get("qa_text_ok", False) else "metadata"
```

**Human Approval Gate** ([graph.py:1473-1502](../../src/lily_books/graph.py#L1473-L1502)):
```python
def route_after_review(state: FlowState) -> str:
    if not state.get("human_approved", False):
        return "end_without_upload"

    # PRIMARY: PublishDrive
    if "publishdrive" in config.target_retailers:
        return "upload_publishdrive"

    # LEGACY: Individual retailers
    ...
```

### 3. Feature Toggles ([src/lily_books/config.py](../../src/lily_books/config.py))

- `ENABLE_QA_REVIEW` - Enable/disable QA validation and remediation
- `ENABLE_AUDIO` - Enable/disable audio production pipeline
- `ENABLE_PUBLISHING` - Enable/disable publishing/distribution
- `TARGET_RETAILERS` - Select retailers (publishdrive, amazon, google, draft2digital)

### 4. State Management ([src/lily_books/models.py:416-454](../../src/lily_books/models.py#L416-L454))

**FlowState TypedDict**:
```python
class FlowState(TypedDict):
    slug: str
    book_id: int | None
    raw_text: str | None
    chapters: list[ChapterSplit] | None
    rewritten: list[ChapterDoc] | None
    qa_text_ok: bool | None
    audio_ok: bool | None
    epub_path: str | None
    publishing_metadata: PublishingMetadata | dict | None
    target_retailers: list[str] | None
    identifiers: dict | None
    upload_results: dict | None
    # ... and many more fields
```

### 5. Async Processing ([graph.py:148-330](../../src/lily_books/graph.py#L148-L330))

**Parallel Chapter Processing**:
- asyncio.Semaphore(3) limits concurrent OpenRouter API calls
- asyncio.wait_for() handles timeouts
- asyncio.gather() processes chapters in parallel
- Skips already-completed chapters on resume

**Rate Limiting**:
```python
semaphore = asyncio.Semaphore(3)
async def rate_limited_chapter(task, chapter_num, index):
    async with semaphore:
        result = await asyncio.wait_for(task, timeout=timeout)
```

### 6. Checkpointing ([graph.py:1518-1530](../../src/lily_books/graph.py#L1518-L1530))

**SqliteSaver for Persistence**:
```python
checkpoint_db = paths["meta"] / "checkpoints.db"
conn = sqlite3.connect(str(checkpoint_db), check_same_thread=False)
checkpointer = SqliteSaver(conn)
return graph.compile(checkpointer=checkpointer)
```

**Resume Optimization**:
- Checks for existing chapter docs before rewriting
- Checks for existing QA results before re-validating
- Saves costs by avoiding redundant LLM calls

### 7. Error Handling ([src/lily_books/models.py:8-88](../../src/lily_books/models.py#L8-L88))

**PipelineError Hierarchy**:
- `IngestError` - Book ingestion failures
- `ChapterizeError` - Chapter splitting failures
- `RewriteError` - Text modernization failures
- `QAError` - QA validation failures
- `EPUBError` - EPUB generation failures
- `TTSError` - TTS generation failures
- `MasterError` - Audio mastering failures
- `PackageError` - Final packaging failures
- `CoverError` - Cover generation failures
- `PublishingError` - Publishing/distribution failures
- `UploadError` - Retailer upload failures
- `ValidationError` - Validation failures

## Key Files

- [src/lily_books/graph.py](../../src/lily_books/graph.py) - Complete state machine (1531 lines)
- [src/lily_books/models.py](../../src/lily_books/models.py) - FlowState, error models
- [src/lily_books/runner.py](../../src/lily_books/runner.py) - Pipeline execution
- [src/lily_books/storage.py](../../src/lily_books/storage.py) - State persistence
- [src/lily_books/config.py](../../src/lily_books/config.py) - Feature toggles

## Common Questions

### Q: How do I add a new node to the pipeline?

**Answer**:
1. Define node function with signature: `def my_node(state: FlowState) -> FlowState`
2. Update state and return: `return {**state, "my_field": value}`
3. Add to graph in `build_graph()`: `graph.add_node("my_node", my_node)`
4. Add edge: `graph.add_edge("previous_node", "my_node")`
5. Handle errors with custom PipelineError subclass
6. Add logging with `append_log_entry()`
7. Update FlowState TypedDict with new fields

**Example** ([graph.py:927-987](../../src/lily_books/graph.py#L927-L987)):
```python
def metadata_node(state: FlowState) -> FlowState:
    """Generate publishing metadata using LLM."""
    append_log_entry(state["slug"], {"node": "metadata", "status": "started"})

    try:
        pub_metadata = generate_metadata(...)
        append_log_entry(state["slug"], {"node": "metadata", "status": "completed"})
        return {**state, "publishing_metadata": pub_metadata}
    except Exception as e:
        append_log_entry(state["slug"], {"node": "metadata", "status": "error"})
        logger.warning(f"Metadata generation failed: {e}")
        return state  # Non-critical - continue without metadata
```

---

### Q: How do conditional edges work?

**Answer**:
Conditional edges allow dynamic routing based on state:

```python
def should_remediate(state: FlowState) -> str:
    return "remediate" if not state.get("qa_text_ok", False) else "metadata"

graph.add_conditional_edges(
    "qa_text",  # Source node
    should_remediate,  # Router function
    {
        "remediate": "remediate",  # If QA failed
        "metadata": "metadata"  # If QA passed
    }
)
```

The router function returns a **key** from the edge mapping.

---

### Q: How do I modify the publishing pipeline flow?

**Answer**:
1. Publishing nodes are only added if `config.enable_publishing` is True
2. Modify routing in [graph.py:1473-1513](../../src/lily_books/graph.py#L1473-L1513)
3. Current flow after human review:
   - **PRIMARY**: PublishDrive (single upload) → report
   - **LEGACY**: Amazon → Google → D2D → report
4. Add new retailer: Create uploader node, add to conditional routing
5. Test with `ENABLE_PUBLISHING=true TARGET_RETAILERS=publishdrive`

---

### Q: What's the difference between sync and async nodes?

**Answer**:

**Sync nodes** (`rewrite_node`):
- Process chapters sequentially
- Simple, predictable execution
- Used when parallelism not beneficial

**Async nodes** (`rewrite_node_async`):
- Process chapters in parallel (limited by semaphore)
- 3x faster for multi-chapter books
- Handles timeouts with asyncio.wait_for()
- Used in production for speed

Both skip already-completed chapters on resume.

---

### Q: How do feature toggles work?

**Answer**:
Feature toggles control which nodes are added to the graph ([graph.py:1373-1407](../../src/lily_books/graph.py#L1373-L1407)):

```python
config = get_config()

# Always add core nodes
graph.add_node("ingest", ingest_node)
graph.add_node("chapterize", chapterize_node)
graph.add_node("rewrite", rewrite_node)

# Optional QA nodes
if config.enable_qa_review:
    graph.add_node("qa_text", qa_text_node)
    graph.add_node("remediate", remediate_node)

# Optional audio nodes
if config.enable_audio:
    graph.add_node("tts", tts_node)
    graph.add_node("master", master_node)

# Optional publishing nodes
if config.enable_publishing:
    graph.add_node("assign_identifiers", assign_identifiers_node)
    # ... etc
```

Set in `.env`:
```bash
ENABLE_QA_REVIEW=true
ENABLE_AUDIO=false
ENABLE_PUBLISHING=true
TARGET_RETAILERS=publishdrive
```

---

### Q: How does checkpointing work?

**Answer**:
Checkpoints save pipeline state for resume:

1. **Create checkpoint DB** per project: `books/{slug}/meta/checkpoints.db`
2. **SqliteSaver** persists state after each node
3. **Resume** by running pipeline again with same slug
4. **Skip completed work**: Nodes check for existing results

Example skip logic ([graph.py:391-408](../../src/lily_books/graph.py#L391-L408)):
```python
existing_doc = load_chapter_doc(state["slug"], chapter_split.chapter)
if existing_doc:
    # Chapter already completed - skip rewrite
    rewritten_chapters.append(existing_doc)
    skipped_chapters.append(chapter_split.chapter)
    continue
```

---

### Q: How do I debug pipeline failures?

**Answer**:

1. **Check Langfuse traces**: Every node emits debug events
2. **Read ingestion log**: `books/{slug}/meta/ingestion_log.jsonl`
3. **Check checkpoint state**: `books/{slug}/meta/ingestion_state.json`
4. **Review chapter failures**: Logged in ingestion_state.json
5. **Inspect error context**: PipelineError includes slug, node, context

Example error logging ([graph.py:92-101](../../src/lily_books/graph.py#L92-L101)):
```python
except Exception as e:
    append_log_entry(state["slug"], {"node": "ingest", "status": "error"})
    raise IngestError(
        f"Ingest failed: {str(e)}",
        slug=state["slug"],
        node="ingest",
        context={"book_id": state["book_id"]}
    )
```

---

## Best Practices

### 1. Always Update FlowState
When adding fields, update the TypedDict in [models.py:416-454](../../src/lily_books/models.py#L416-L454)

### 2. Log Everything
Use `append_log_entry()` for node status (started, completed, error, skipped)

### 3. Handle Errors Gracefully
- Critical nodes: Raise PipelineError subclass
- Non-critical nodes: Log warning and continue

### 4. Support Resume
Check for existing results before expensive operations

### 5. Use Feature Toggles
Make new features optional via config flags

### 6. Test with Real Data
Run with single chapter first: `--chapters 1`

### 7. Monitor with Langfuse
Use debug events for observability

---

## Related Agents

- [/llm-chains](llm-chains.md) - For LLM operations within nodes
- [/publishing](publishing.md) - For publishing node details
- [/testing](testing.md) - For pipeline testing strategies

---

**Last Updated**: 2025-10-25
**Version**: 1.0
