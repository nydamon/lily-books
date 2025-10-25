# Quality Assurance Agent

**Command**: `/qa-validation`

## Purpose

Expert in text QA, validation gates, and quality metrics for the Lily Books text modernization pipeline.

## Key Knowledge Areas

### 1. QA System Overview

**Purpose**: Validate that modernized text preserves meaning, readability, and formatting

**Model**: Claude 4.5 Haiku via OpenRouter (temperature 0.0 for consistency)

**Strategy**: Graduated quality gates with flexible thresholds

### 2. Quality Metrics

**Fidelity Score** (0-100):
- Target: ≥92/100
- Measures meaning preservation
- LLM-based comparison of original vs modern
- Most critical metric

**Readability Grade** (Flesch-Kincaid):
- Target: 7-9 (middle school level)
- Balance accessibility with literary quality
- Calculated with textstat library

**Character Count Ratio**:
- Target: 1.10-1.40
- Modern text should be 10-40% longer
- Indicates proper expansion/clarification

**Formatting Preservation**:
- Quote count match
- Italics/emphasis preservation
- Dialogue structure maintained

### 3. QA Report Structure ([models.py:90-131](../../src/lily_books/models.py#L90-L131))

```python
class QAReport(BaseModel):
    fidelity_score: int | None
    readability_grade: float | None
    readability_appropriate: bool | None
    character_count_ratio: float | None
    modernization_complete: bool | None
    formatting_preserved: bool | None
    tone_consistent: bool | None
    quote_count_match: bool | None
    emphasis_preserved: bool | None
    literary_quality_maintained: bool | None
    historical_accuracy_preserved: bool | None
    issues: list[QAIssue]
    confidence: float | None
    llm_reasoning: str | None
```

### 4. Graduated Quality Gates ([checker.py:137-200](../../src/lily_books/chains/checker.py#L137-L200))

**Evaluation Logic**:
1. Aggregate metrics across all paragraph pairs
2. Check against thresholds (min_fidelity, readability_range)
3. Count critical issues
4. Determine pass/fail per chapter

**Soft Validation** (default):
- Log warnings for failures
- Continue processing other chapters
- Enable remediation for failed chapters

**Hard Validation** (optional):
- Stop pipeline on first failure
- Requires manual intervention

### 5. Remediation Strategy ([graph.py:837-925](../../src/lily_books/graph.py#L837-L925))

**How It Works**:
1. Identify failed chapters from qa_text_node
2. Load original chapter data
3. Rerun rewrite_chapter() with enhanced prompts
4. Rerun qa_chapter() validation
5. Clear failure if passed, track if still failing

**Enhanced Prompts**:
- Include specific issues from previous QA report
- Request focused improvements
- Maintain all other quality aspects

## Key Files

- [src/lily_books/chains/checker.py](../../src/lily_books/chains/checker.py) - QA validation (Claude Haiku)
- [src/lily_books/models.py](../../src/lily_books/models.py) - QAReport, QAIssue, QualityControl
- [src/lily_books/utils/validators.py](../../src/lily_books/utils/validators.py) - Output validation
- [docs/QA_CRITERIA.md](../../docs/QA_CRITERIA.md) - Quality criteria documentation
- [src/lily_books/graph.py](../../src/lily_books/graph.py) - qa_text_node, remediate_node

## Common Questions

### Q: How do I adjust quality thresholds for a specific book?

**Answer**:

Use QualityControl overrides in book metadata:

```python
# books/{slug}/meta/book.yaml
quality_control:
  min_fidelity: 90  # Lower from default 92
  target_fidelity: 95
  readability_range: [6.5, 9.5]  # Widen from default [7, 9]
  failure_mode: "soft"  # Continue on errors
  notes: "Historical fiction needs period-appropriate language"
```

**Common Adjustments**:
- **Complex classics** (Dickens, Austen): Lower min_fidelity to 88-90
- **Simple narratives**: Raise min_fidelity to 94-96
- **Young readers**: Lower readability_range to [6, 8]
- **Advanced readers**: Raise readability_range to [8, 10]

### Q: Why are chapters failing QA?

**Answer**:

Check the QA issues in detail:

```bash
# View QA report for chapter 1
cat books/{slug}/work/qa/text/ch01-issues.json
```

**Common Failure Reasons**:

1. **Low Fidelity** (<92):
   - Meaning changed too much
   - Details omitted
   - Dialogue altered
   - **Fix**: Rewrite with stricter fidelity requirements

2. **Readability Too High** (>9):
   - Language still too complex
   - Archaic phrases remain
   - **Fix**: Rewrite with simpler vocabulary

3. **Formatting Lost**:
   - Quotes not preserved
   - Italics stripped
   - **Fix**: Rewrite preserving formatting markers

4. **Modernization Incomplete**:
   - Archaic language detected
   - Old idioms remain
   - **Fix**: Enhance modernization prompt

**Debug with Langfuse**:
- Check trace URL in error logs
- View exact QA input/output
- Analyze LLM reasoning

### Q: How does soft validation work?

**Answer**:

**Soft Validation** (default, `failure_mode: "soft"`):
- Chapters that fail QA are logged but don't stop pipeline
- Failed chapters tracked in state.failed_chapters
- Remediation node attempts to fix them
- Pipeline completes even if some chapters still fail
- User can manually review/edit failed chapters later

**Hard Validation** (`failure_mode: "hard"`):
- First QA failure stops entire pipeline
- Raises QAError immediately
- Requires fixing before continuing
- More strict, ensures all-or-nothing quality

**When to Use Each**:
- **Soft** (recommended): Iterative improvement, complete drafts
- **Hard**: Production releases, strict quality requirements

### Q: How does remediation work?

**Answer**:

**Remediation Flow** ([graph.py:837-925](../../src/lily_books/graph.py#L837-L925)):

1. **Trigger**: qa_text_node returns failed_chapters list
2. **Router**: Conditional edge routes to remediate_node
3. **Remediate**:
   - Load original chapter data
   - Analyze failure reasons from QA report
   - Enhance Writer prompt with specific improvements
   - Rewrite chapter
   - Re-run QA validation
4. **Outcome**:
   - **Pass**: Clear failure, mark qa_text_ok=True
   - **Still fail**: Track as still_failing, proceed with warning

**Limits**:
- One remediation attempt per chapter
- Prevents infinite retry loops
- Manual intervention needed if still failing

### Q: How do I customize QA for different book types?

**Answer**:

**Historical Fiction**:
```yaml
quality_control:
  min_fidelity: 94  # Stricter preservation
  readability_range: [7.5, 9]  # Slightly higher reading level
  notes: "Preserve period-appropriate dialogue"
```

**Children's Classics**:
```yaml
quality_control:
  min_fidelity: 90  # Allow more simplification
  readability_range: [6, 8]  # Lower reading level
  notes: "Prioritize accessibility over fidelity"
```

**Literary Classics** (Joyce, Woolf):
```yaml
quality_control:
  min_fidelity: 88  # Complex prose needs more flexibility
  readability_range: [8, 10]  # Higher reading level acceptable
  notes: "Preserve stream-of-consciousness style"
```

## Best Practices

### 1. Start with Default Thresholds
- Let first book complete with defaults
- Analyze results
- Adjust for subsequent books

### 2. Use Soft Validation
- Enables iterative improvement
- Provides complete drafts
- Manual review of failures

### 3. Monitor Langfuse Traces
- Understand why QA passed/failed
- Optimize prompts based on patterns
- Track quality trends over time

### 4. Customize Per Book Type
- Different thresholds for different genres
- Document rationale in quality_control.notes

### 5. Review Remediation Results
- Check if second attempt improved
- Manual fix if remediation fails
- Update prompts for future books

## Related Agents

- [/llm-chains](llm-chains.md) - For Checker chain details
- [/langgraph-pipeline](langgraph-pipeline.md) - For QA node flow
- [/testing](testing.md) - For testing QA validation

---

**Last Updated**: 2025-10-25
**Version**: 1.0
