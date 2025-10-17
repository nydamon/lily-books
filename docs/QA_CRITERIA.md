# Quality Assurance Criteria

This document defines the acceptance thresholds and validation criteria for the Lily Books modernization pipeline.

## Text Modernization QA

### Fidelity Score
- **Target**: ≥92/100
- **Method**: LLM-based comparison between original and modernized text
- **Model**: Claude Sonnet (independent from writer model)
- **Criteria**: Semantic preservation, meaning accuracy, context maintenance

### Readability Grade
- **Target**: 7-9 (Flesch-Kincaid)
- **Method**: Automated calculation using textstat library
- **Purpose**: Ensure text is accessible to target student audience
- **Range**: Grade 7 (junior high) to Grade 9 (high school freshman)

### Character Count Ratio
- **Target**: 1.10-1.40 (narrative), 0.90-1.40 (dialogue)
- **Method**: `len(modernized) / len(original)`
- **Purpose**: Ensure modernization adds appropriate length without excessive verbosity
- **Dialogue Exception**: Dialogue may be shorter due to archaic speech patterns

### Formatting Preservation

#### Quote Count Parity
- **Target**: Exact match
- **Method**: Count normalized quotes (`"` and `'`) in original vs modernized
- **Normalization**: Convert smart quotes to standard quotes for comparison
- **Critical**: All dialogue must preserve quote structure

#### Emphasis Preservation
- **Target**: Exact match
- **Method**: Count `_text_` patterns in original vs modernized
- **Purpose**: Preserve italicized text (book titles, emphasis, foreign words)
- **Implementation**: Regex pattern matching

### Archaic Phrase Detection
- **Target**: Zero missed archaic phrases
- **Patterns**:
  - `\bto-day\b` → "today"
  - `\ba fortnight\b` → "two weeks"
  - `\bupon my word\b` → "indeed" or "certainly"
  - `\bsaid (he|she)\b` → "he/she said"
- **Method**: Regex pattern matching on modernized text
- **Severity**: High (indicates incomplete modernization)

### Tone Consistency
- **Target**: Maintained
- **Method**: LLM evaluation
- **Criteria**: Formal/informal balance, narrative voice, character voice consistency

## Audio QA

### ACX Compliance
- **RMS Level**: -20dB ±2dB
- **Peak Level**: ≤-3dB
- **Noise Floor**: ≤-60dB
- **Method**: ffmpeg volumedetect analysis
- **Purpose**: Ensure audiobook meets Audible/ACX technical requirements

### Audio Quality Metrics
- **Sample Rate**: 44.1kHz
- **Bit Depth**: 16-bit minimum
- **Channels**: Mono
- **Format**: MP3 CBR 192kbps
- **Method**: ffmpeg analysis and validation

### Retail Sample
- **Duration**: 3 minutes (180 seconds)
- **Start Time**: 30 seconds into first chapter
- **Purpose**: Provide preview for potential buyers
- **Format**: Same specifications as full audiobook

## Validation Workflow

### Automated Checks
1. **Local Validation**: Quote parity, emphasis parity, archaic detection, ratio calculation
2. **LLM Validation**: Fidelity score, tone consistency, readability assessment
3. **Audio Validation**: ACX compliance, technical specifications

### Human-in-the-Loop (HITL)
1. **QA Queue**: Failed paragraphs flagged for manual review
2. **Edit Interface**: API endpoints for manual text correction
3. **Approval Workflow**: Human approval required for final publication

### Remediation Process
1. **Automatic Retry**: Failed paragraphs retried with enhanced prompts
2. **Targeted Fixes**: Specific issue types get specialized remediation
3. **Manual Override**: Human editors can bypass automated fixes

## Acceptance Thresholds Summary

| Metric | Target | Method | Severity |
|--------|--------|--------|----------|
| Fidelity Score | ≥92/100 | LLM | High |
| Readability Grade | 7-9 | Automated | Medium |
| Character Ratio | 1.10-1.40 | Automated | Medium |
| Quote Parity | Exact | Automated | High |
| Emphasis Parity | Exact | Automated | High |
| Archaic Phrases | 0 | Automated | High |
| Tone Consistency | Maintained | LLM | Medium |
| ACX RMS | -20dB ±2dB | Automated | High |
| ACX Peak | ≤-3dB | Automated | High |

## Quality Gates

### Pre-Publication Checklist
- [ ] All chapters pass fidelity threshold (≥92)
- [ ] All chapters pass formatting checks (quotes, emphasis)
- [ ] No archaic phrases remain
- [ ] Readability within target range (7-9)
- [ ] Audio meets ACX specifications
- [ ] Retail sample extracted and validated
- [ ] EPUB validates without errors
- [ ] Human review completed for flagged content

### Rollback Criteria
- Fidelity score <85 for any chapter
- Critical formatting errors (missing quotes, broken emphasis)
- Audio fails ACX compliance
- EPUB validation errors
- Human reviewer rejection

## Continuous Improvement

### Metrics Tracking
- Track QA pass rates over time
- Monitor common failure patterns
- Analyze cost vs quality tradeoffs
- Collect human feedback on output quality

### Model Updates
- Regular evaluation of new LLM models
- A/B testing of prompt improvements
- Performance benchmarking
- Cost optimization

### Process Refinement
- Refine remediation strategies
- Improve error detection
- Optimize human review workflow
- Enhance automation where possible

