# Technical Specification

## System Overview

Lily Books is a LangChain/LangGraph pipeline that modernizes 19th-century public-domain texts into student-friendly English while preserving meaning, dialogue structure, and literary elements. The system produces both EPUB ebooks and ACX-compliant audiobooks.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gutendex API  │───▶│  LangGraph State │───▶│  Output Files    │
│                 │    │     Machine      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   LangChain     │
                    │   Chains        │
                    │                 │
                    │ • Writer Chain  │
                    │ • Checker Chain │
                    │ • Ingest Chain  │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   LLM Services  │
                    │                 │
                    │ • OpenAI GPT-4o │
                    │ • Anthropic     │
                    │   Claude Sonnet 4.5 │
                    │ • ElevenLabs    │
                    └─────────────────┘
```

### State Machine Flow

```
Ingest → Chapterize → Rewrite → QA Text → Remediate → EPUB Build → TTS → Master → QA Audio → Package
   │         │          │         │          │           │         │       │         │         │
   ▼         ▼          ▼         ▼          ▼           ▼         ▼       ▼         ▼         ▼
Raw Text  Chapters  Modernized  Validated  Corrected   EPUB     Audio   Mastered  Verified  Final
          Splits    Chapters    Chapters   Chapters    File     Files   Audio     Audio     Deliverables
```

## Data Models

### Core Models

#### BookMetadata
```python
class BookMetadata(BaseModel):
    title: str
    author: str
    public_domain_source: str
    language: str = "en-US"
    voice: Dict[str, Any] = Field(default_factory=lambda: {
        "provider": "elevenlabs",
        "voice_id": "2EiwWnXFnvU5JabPnv8n"
    })
    acx: Dict[str, Any] = Field(default_factory=lambda: {
        "target_rms_db": -20,
        "peak_limit_db": -3
    })
```

#### ChapterSplit
```python
class ChapterSplit(BaseModel):
    chapter: int
    title: str
    paragraphs: List[str]
```

#### ChapterDoc
```python
class ChapterDoc(BaseModel):
    chapter: int
    title: str
    pairs: List[ParaPair]
```

#### ParaPair
```python
class ParaPair(BaseModel):
    i: int
    para_id: str
    orig: str
    modern: str
    qa: Optional[QAReport] = None
    notes: Optional[str] = None
```

#### QAReport
```python
class QAReport(BaseModel):
    fidelity_score: int = Field(ge=0, le=100)
    readability_grade: float
    readability_appropriate: bool
    character_count_ratio: float
    modernization_complete: bool
    formatting_preserved: bool
    tone_consistent: bool
    quote_count_match: bool
    emphasis_preserved: bool
    literary_quality_maintained: bool
    historical_accuracy_preserved: bool
    issues: List[QAIssue] = Field(default_factory=list)
    retry_count: int = 0
```

### LLM Output Models

#### WriterOutput
```python
class WriterOutput(BaseModel):
    paragraphs: List[ModernizedParagraph] = Field(
        description="Array of modernized paragraphs in order"
    )
```

#### CheckerOutput
```python
class CheckerOutput(BaseModel):
    fidelity_score: int = Field(ge=0, le=100)
    readability_grade: float
    readability_appropriate: bool
    modernization_complete: bool
    formatting_preserved: bool
    tone_consistent: bool
    quote_count_match: bool
    emphasis_preserved: bool
    character_count_ratio: float
    literary_quality_maintained: bool
    historical_accuracy_preserved: bool
    issues: List[QAIssue] = Field(default_factory=list)
```

#### ModernizedParagraph
```python
class ModernizedParagraph(BaseModel):
    modern: str = Field(description="Modernized version of the paragraph")
```

#### QAIssue
```python
class QAIssue(BaseModel):
    type: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    span_original: Optional[str] = None
    span_modern: Optional[str] = None
    suggestion: Optional[str] = None
```

## API Specification

### Base URL
```
http://localhost:8000
```

### Authentication
None required for local development.

### Endpoints

#### Project Management

##### Create Project
```http
POST /api/projects
Content-Type: application/json

{
  "slug": "pride-prejudice",
  "book_id": 1342
}
```

**Response:**
```json
{
  "slug": "pride-prejudice",
  "book_id": 1342,
  "status": "created",
  "created_at": "2024-12-19T10:00:00Z"
}
```

##### Get Project Status
```http
GET /api/projects/{slug}/status
```

**Response:**
```json
{
  "slug": "pride-prejudice",
  "status": "completed",
  "progress": {
    "chapters_total": 61,
    "chapters_completed": 61,
    "chapters_failed": 0
  },
  "last_updated": "2024-12-19T10:00:00Z"
}
```

#### Chapter Management

##### Get Chapter Pairs
```http
GET /api/projects/{slug}/chapters/{chapter}/pairs
```

**Response:**
```json
{
  "chapter": 1,
  "title": "Chapter 1",
  "pairs": [
    {
      "i": 0,
      "para_id": "ch01_para000",
      "orig": "It is a truth universally acknowledged...",
      "modern": "It is a truth universally acknowledged...",
      "qa": {
        "fidelity_score": 95,
        "readability_appropriate": true,
        "formatting_preserved": true
      }
    }
  ]
}
```

##### Update Modern Text
```http
PATCH /api/projects/{slug}/chapters/{chapter}/pairs/{i}
Content-Type: application/json

{
  "modern": "Updated modernized text"
}
```

**Response:**
```json
{
  "i": 0,
  "para_id": "ch01_para000",
  "orig": "It is a truth universally acknowledged...",
  "modern": "Updated modernized text",
  "updated_at": "2024-12-19T10:00:00Z"
}
```

#### Quality Assurance

##### Get QA Summary
```http
GET /api/projects/{slug}/qa/summary
```

**Response:**
```json
{
  "total_chapters": 61,
  "chapters_passed": 58,
  "chapters_failed": 3,
  "average_fidelity": 94.2,
  "issues_by_type": {
    "formatting": 12,
    "readability": 5,
    "tone": 3
  }
}
```

#### Health Check

##### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-19T10:00:00Z",
  "version": "1.0.0"
}
```

## Configuration

### Environment Variables

#### Required
```env
# API Keys
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
```

#### Optional
```env
# Model Configuration
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
ELEVENLABS_VOICE_ID=2EiwWnXFnvU5JabPnv8n

# Fallback Models
OPENAI_FALLBACK_MODEL=gpt-4o-mini
ANTHROPIC_FALLBACK_MODEL=claude-haiku-4-5-20251001

# Caching
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
CACHE_TYPE=memory
REDIS_URL=redis://localhost:6379

# Observability
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com

# Development
DEBUG=false
LOG_LEVEL=INFO
```

### Configuration Schema
```python
class Settings(BaseSettings):
    # API Keys
    openai_api_key: str
    anthropic_api_key: str
    elevenlabs_api_key: str
    
    # Models
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    elevenlabs_voice_id: str = "2EiwWnXFnvU5JabPnv8n"
    
    # Fallback Models
    openai_fallback_model: str = "gpt-4o-mini"
    anthropic_fallback_model: str = "claude-haiku-4-5-20251001"
    
    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_type: str = "memory"
    redis_url: str = "redis://localhost:6379"
    
    # Observability
    langfuse_enabled: bool = True
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    
    # Development
    debug: bool = False
    log_level: str = "INFO"
```

## File Structure

### Project Layout
```
books/{slug}/
├── source/
│   └── original.txt          # Raw text from Gutendex
├── work/
│   ├── chapters.jsonl        # Chapter splits
│   ├── rewrite/
│   │   ├── ch01.json         # Modernized chapters
│   │   └── ...
│   ├── audio/
│   │   ├── ch01.wav          # TTS audio files
│   │   └── ...
│   ├── audio_mastered/
│   │   ├── ch01.mp3          # Mastered audio
│   │   └── ...
│   └── qa/
│       ├── text/
│       │   ├── ch01-issues.json  # QA issues
│       │   └── ...
│       └── audio/
│           ├── ch01-meters.json  # Audio metrics
│           └── ...
├── deliverables/
│   ├── ebook/
│   │   └── {slug}.epub       # Final EPUB
│   └── audio/
│       └── {slug}_retail_sample.mp3  # Retail sample
└── meta/
    ├── book.yaml              # Book metadata
    ├── publish.json           # Publishing metadata
    ├── ingestion_log.jsonl    # Processing log
    ├── ingestion_state.json   # Pipeline state
    ├── checkpoints.db         # LangGraph state
    └── chapter_failures.jsonl # Failure tracking
```

### Source Code Layout
```
src/lily_books/
├── __init__.py
├── api/
│   ├── __init__.py
│   └── main.py               # FastAPI application
├── chains/
│   ├── __init__.py
│   ├── ingest.py             # Text ingestion chain
│   ├── writer.py             # Text modernization chain
│   └── checker.py            # Quality assurance chain
├── config.py                 # Configuration management
├── graph.py                  # LangGraph state machine
├── models.py                 # Pydantic data models
├── observability.py          # Observability callbacks
├── runner.py                 # Pipeline runner
├── storage.py                # File storage utilities
├── tools/
│   ├── __init__.py
│   ├── epub.py               # EPUB generation
│   ├── tts.py                # Text-to-speech
│   └── audio.py              # Audio processing
└── utils/
    ├── __init__.py
    ├── cache.py              # LLM caching
    ├── llm_factory.py        # LLM factory with fallbacks
    ├── retry.py              # Advanced retry logic
    ├── tokens.py             # Token counting utilities
    └── validators.py         # Output validation
```

## Quality Assurance

### Text QA Metrics

#### Fidelity Score
- **Target**: ≥92/100
- **Method**: LLM-based comparison
- **Validation**: Semantic similarity analysis

#### Readability
- **Target**: Grade 7-9
- **Method**: Flesch-Kincaid analysis
- **Validation**: Automated grade calculation

#### Character Ratio
- **Target**: 1.10-1.40
- **Method**: Length comparison
- **Validation**: Ratio calculation

#### Formatting Preservation
- **Target**: 100% preservation
- **Method**: Quote and emphasis detection
- **Validation**: Pattern matching

### Audio QA Metrics

#### ACX Compliance
- **RMS Levels**: -20dB target
- **Peak Limits**: -3dB maximum
- **Method**: FFmpeg analysis
- **Validation**: Automated compliance checking

#### Audio Metrics
- **Volume Detection**: RMS and peak analysis
- **Duration**: Chapter length validation
- **Quality**: Audio quality assessment

## Performance Requirements

### Response Times
- **API Endpoints**: <500ms for simple operations
- **Chapter Processing**: <30 seconds per chapter
- **Pipeline Completion**: <2 hours for typical book

### Throughput
- **Concurrent Requests**: 10+ simultaneous
- **Chapter Processing**: 2+ chapters per minute
- **Batch Processing**: 100+ paragraphs per batch

### Resource Usage
- **Memory**: <2GB for typical book
- **Disk Space**: <500MB per book
- **CPU**: Efficient batch processing

## Security Considerations

### API Key Management
- Environment variable storage
- No hardcoded credentials
- Secure key rotation

### Input Validation
- Pydantic model validation
- Sanitization of user inputs
- Rate limiting on API endpoints

### Error Handling
- Safe error messages
- No sensitive data exposure
- Comprehensive logging

## Monitoring and Observability

### Metrics
- **Cost Tracking**: Token usage and API costs
- **Performance**: Response times and throughput
- **Quality**: QA scores and error rates
- **Reliability**: Success/failure rates

### Logging
- **Structured Logging**: JSON format
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Log Rotation**: Automatic rotation
- **Centralized Logging**: Langfuse integration

### Alerting
- **Error Rates**: Threshold-based alerting
- **Performance**: Response time monitoring
- **Cost**: Budget threshold alerts
- **Quality**: QA score degradation

## Deployment

### Prerequisites
- Python 3.11+
- Poetry
- FFmpeg
- Redis (optional)

### Installation
```bash
# Clone repository
git clone https://github.com/nydamon/lily-books.git
cd lily-books

# Install dependencies
poetry install

# Configure environment
cp env.example .env
# Edit .env with API keys

# Activate environment
poetry shell
```

### Running
```bash
# Start API server
poetry run python -m src.lily_books.api.main

# Run pipeline
python -c "from src.lily_books.runner import run_pipeline; run_pipeline('test-book', 1342)"
```

### Docker (Future)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install poetry && poetry install
CMD ["poetry", "run", "python", "-m", "src.lily_books.api.main"]
```

## Testing

### Test Structure
```
tests/
├── __init__.py
├── fixtures/
│   └── sample_chapter.py
├── test_chains.py           # Chain behavior tests
├── test_models.py           # Pydantic model tests
├── test_tools.py            # Tool functionality tests
├── test_utils.py            # Utility module tests
└── test_graph_nodes.py      # Graph node tests
```

### Test Categories
- **Unit Tests**: Individual function testing
- **Integration Tests**: Chain and workflow testing
- **Model Tests**: Pydantic validation testing
- **API Tests**: Endpoint functionality testing

### Test Coverage
- **Target**: >90% code coverage
- **Tools**: pytest, coverage
- **CI/CD**: Automated testing on PRs

## Maintenance

### Regular Tasks
- **Dependency Updates**: Monthly security updates
- **Performance Monitoring**: Weekly performance reviews
- **Cost Analysis**: Monthly cost optimization
- **Quality Reviews**: Quarterly quality assessments

### Backup Strategy
- **Code**: Git repository
- **Data**: Regular backups of book data
- **Configuration**: Environment variable backups
- **Logs**: Log retention policies

### Disaster Recovery
- **Backup Restoration**: Automated restore procedures
- **Service Continuity**: Fallback service options
- **Data Recovery**: Point-in-time recovery
- **Communication**: Incident response procedures

---

*Last Updated: 2025-01-02*
*Version: 1.1.0*
*Status: Production Ready*
