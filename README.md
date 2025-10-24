# Lily Books

A LangChain/LangGraph pipeline for modernizing public-domain books into student-friendly English, with EPUB and audiobook generation.

## Overview

Lily Books converts 19th-century public-domain texts into modern English suitable for students, while preserving the original meaning, dialogue structure, and literary elements. The pipeline produces both EPUB ebooks and ACX-compliant audiobooks.

## Features

- **Text Modernization**: GPT-4o-mini powered modernization with fidelity preservation via OpenRouter
- **Quality Assurance**: Claude 4.5 Haiku validation with comprehensive quality checks
- **EPUB Generation**: Professional ebook creation with proper formatting and navigation
- **Audiobook Creation**: Fish Audio TTS with ACX-compliant mastering
- **Langfuse Observability**: Complete tracing, cost tracking, and performance monitoring
- **Debug Integration**: Trace IDs in logs, clickable trace URLs in errors
- **OpenRouter Architecture**: Single API for all LLM operations with unified billing
- **Production-Ready**: Structured outputs, caching, fallback models, and self-healing retry logic

## Architecture

The pipeline uses LangGraph to orchestrate the following steps:

1. **Ingest**: Load text from Project Gutenberg via Gutendex API
2. **Chapterize**: Split text into chapters with smart detection
3. **Rewrite**: Modernize text using GPT-4o-mini (via OpenRouter) with parallel batching
4. **QA Text**: Validate quality using Claude 4.5 Haiku (via OpenRouter) with comprehensive checks *(optional, configurable)*
5. **Remediate**: Retry failed chapters with enhanced prompts *(optional, configurable)*
6. **Metadata**: Generate publishing metadata and descriptions
7. **Cover**: Generate Ideogram AI book cover with automated validation
8. **EPUB**: Build professional ebook with ebooklib
9. **TTS**: Synthesize audio using Fish Audio API *(optional, configurable)*
10. **Master**: Apply ACX-compliant audio mastering *(optional, configurable)*
11. **QA Audio**: Validate audio metrics and compliance *(optional, configurable)*
12. **Package**: Create final deliverables and retail samples *(optional, configurable)*

### Pipeline Feature Toggles

The pipeline can be customized by enabling or disabling optional features via environment variables:

**QA Review (`ENABLE_QA_REVIEW`)**
- When `true` (default): Runs QA text validation and remediation steps
- When `false`: Skips QA validation and remediation, proceeding directly from rewrite to metadata generation
- Use case: Disable for faster testing or when you trust the rewrite quality

**Audio Generation (`ENABLE_AUDIO`)**
- When `true` (default): Runs full audio pipeline (TTS, mastering, QA audio, packaging)
- When `false`: Skips all audio steps, pipeline ends after EPUB generation
- Use case: Disable for ebook-only production or to save on TTS costs during development

**Example Configurations:**
```bash
# Ebook only, no QA (fastest)
ENABLE_QA_REVIEW=false
ENABLE_AUDIO=false

# Ebook + Audio, skip QA
ENABLE_QA_REVIEW=false
ENABLE_AUDIO=true

# Full production pipeline (default)
ENABLE_QA_REVIEW=true
ENABLE_AUDIO=true
```

## Installation

### Prerequisites

- Python 3.11+
- Poetry
- ffmpeg (for audio processing)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/nydamon/lily-books.git
cd lily-books
```

2. Install dependencies:
```bash
poetry install
```

3. Configure environment:
```bash
cp env.example .env
# Edit .env with your API keys:
# - OPENROUTER_API_KEY (for GPT-4o-mini and Claude 4.5 Haiku)
# - FISH_API_KEY (for text-to-speech)
# - IDEOGRAM_API_KEY (for mandatory AI cover generation)
# - LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY (for observability)
```

4. Test setup:
```bash
poetry shell
```

## Configuration

Create a `.env` file with the following variables:

```bash
# API Keys
OPENROUTER_API_KEY=your_openrouter_api_key_here  # Required: For all LLM operations (GPT, Claude)
FISH_API_KEY=your_fish_audio_api_key_here  # Optional: For text-to-speech (if ENABLE_AUDIO=true)
IDEOGRAM_API_KEY=your_ideogram_api_key_here  # Required: Ideogram AI cover generation

# Model configurations (OpenRouter format)
OPENAI_MODEL=openai/gpt-4o-mini
OPENAI_FALLBACK_MODEL=openai/gpt-4o-mini
ANTHROPIC_MODEL=anthropic/claude-haiku-4.5
ANTHROPIC_FALLBACK_MODEL=anthropic/claude-sonnet-4.5

# Fish Audio TTS Settings
FISH_REFERENCE_ID=  # Optional: Custom voice model ID from Fish Audio playground
USE_AUDIO_TRANSCRIPTION=true  # Enable audio transcription features

# Langfuse Observability (recommended for production)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-key-here
LANGFUSE_HOST=https://cloud.langfuse.com

# Caching settings
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
CACHE_TYPE=memory

# Development settings
DEBUG=false
LOG_LEVEL=INFO

# Pipeline Feature Toggles
ENABLE_QA_REVIEW=true  # Enable/disable QA text validation
ENABLE_AUDIO=true  # Enable/disable audio generation
USE_AI_COVERS=true  # Required: Ideogram AI cover generation
```

**See `env.example` for complete configuration options.**

## Usage

### Command Line

Run the complete pipeline:

```bash
# Single chapter (for testing)
python3 -m lily_books run 11 --slug alice-test --chapters 1

# Multiple chapters
python3 -m lily_books run 11 --slug alice-sample --chapters 1,2,3

# Full book
python3 -m lily_books run 11 --slug alice-wonderland

# Check status
python3 -m lily_books status alice-wonderland
```

### Python API

```python
from lily_books.runner import run_pipeline

result = run_pipeline("alice-wonderland", book_id=11, chapters=[1, 2, 3])
print(f"Success: {result['success']}")
print(f"EPUB: {result['deliverables']['epub_path']}")
```

### FastAPI Server

Start the API server for human-in-the-loop review:

```bash
poetry run python -m lily_books api
```

Server available at `http://localhost:8000` with docs at `http://localhost:8000/docs`.

### API Endpoints

- `POST /api/projects` - Create new project
- `GET /api/projects/{slug}/status` - Get project status
- `GET /api/projects/{slug}/chapters/{chapter}/pairs` - Get paragraph pairs
- `PATCH /api/projects/{slug}/chapters/{chapter}/pairs/{i}` - Update modern text
- `GET /api/projects/{slug}/qa/summary` - Get QA summary
- `GET /api/health` - Health check

## Project Structure

```
books/{slug}/
  source/original.txt          # Raw text from Gutendex
  work/
    chapters.jsonl            # Chapter splits
    rewrite/ch01.json         # Modernized chapters
    audio/ch01.wav            # TTS audio files
    audio_mastered/ch01.mp3   # Mastered audio
    qa/
      text/ch01-issues.json   # QA issues
      audio/ch01-meters.json  # Audio metrics
  deliverables/
    ebook/{slug}.epub         # Final EPUB
    audio/{slug}_retail_sample.mp3  # Retail sample
  meta/
    book.yaml                 # Book metadata
    publish.json              # Publishing metadata
    ingestion_log.jsonl       # Processing log
    ingestion_state.json      # Pipeline state
```

## Quality Assurance

The pipeline includes multiple QA layers:

### Text QA
- **Fidelity Score**: LLM-based comparison (target: ≥92/100)
- **Readability**: Flesch-Kincaid grade (target: 7-9)
- **Character Ratio**: Length comparison (target: 1.10-1.40)
- **Formatting**: Quote and emphasis preservation
- **Archaic Detection**: Identification of missed archaic phrases

### Audio QA
- **ACX Compliance**: RMS levels (-20dB), peak limits (-3dB)
- **Audio Metrics**: Volume detection and analysis
- **Retail Sample**: Automated sample extraction

## LangChain Best Practices Implementation

The pipeline implements comprehensive LangChain best practices for production readiness:

### ✅ **Structured Outputs**
- Pydantic schemas (`WriterOutput`, `CheckerOutput`) with `PydanticOutputParser`
- Type-safe LLM responses with automatic validation
- Better error messages and debugging

### ✅ **LLM Response Caching**
- Semantic caching with `InMemoryCache` or `RedisSemanticCache`
- 30-50% cost reduction on QA reruns and remediation
- Configurable TTL and cache strategies

### ✅ **Token Counting & Context Management**
- Accurate token counting with `tiktoken`
- Context window validation before API calls
- Adaptive batch sizing based on token limits
- Prevents context overflow errors

### ✅ **Fallback Model Configuration**
- `RunnableWithFallbacks` pattern for resilience
- GPT-4o → GPT-4o-mini fallback
- Claude 4.5 Sonnet → Claude 4.5 Haiku fallback
- Continues processing if primary model fails

### ✅ **Output Validation Layer**
- Semantic validation beyond Pydantic schemas
- Paragraph count consistency checks
- Safe fallback handling for malformed responses
- Detailed validation error reporting

### ✅ **Langfuse Observability**
- Production-grade monitoring and tracing
- Cost tracking and performance analytics
- Debugging and optimization insights
- Fallback to custom JSONL logging

### ✅ **Advanced Retry Logic**
- `tenacity` library with exponential backoff
- Jitter to prevent thundering herd effects
- Specialized retry strategies per error type
- Rate limit handling with intelligent backoff

### ✅ **Skip Completed Chapters**
- Resume optimization to avoid redundant work
- Checks existing chapter files before processing
- Significant cost savings on pipeline restarts
- Transparent logging of skipped chapters

## Cost Estimation

Approximate costs per 1,000 words:

- **Modernization**: $0.50-2.00 (GPT-4o) → $0.25-1.00 with caching
- **QA Validation**: $0.15-0.75 (Claude 4.5 Sonnet) → $0.08-0.38 with caching
- **TTS**: Varies (Fish Audio - check pricing at https://fish.audio)
- **Total**: $0.67-2.77 per 1,000 words → $0.35-1.40 with optimizations

**Cost Reduction**: 30-50% savings through caching and adaptive batching

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test suites
poetry run pytest tests/test_utils.py          # Utility modules
poetry run pytest tests/test_graph_nodes.py    # Graph node behavior
poetry run pytest tests/test_models.py         # Pydantic models
poetry run pytest tests/test_chains.py         # LangChain chains

# Run with coverage
poetry run pytest --cov=src/lily_books
```

### Code Formatting

```bash
poetry run black src/ tests/
poetry run ruff check src/ tests/
```

### Adding New Features

1. Create feature branch
2. Implement changes with tests
3. Update documentation
4. Submit pull request

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Langfuse Observability

The pipeline includes **comprehensive Langfuse tracing** for production monitoring:

### What Gets Tracked
- ✅ **All LLM calls** - Every interaction with OpenRouter models
- ✅ **Token usage** - Prompt, completion, and total tokens
- ✅ **Costs** - Automatic cost calculation per model
- ✅ **Latencies** - Time spent in each operation
- ✅ **Errors** - Full context with clickable trace URLs
- ✅ **Quality metrics** - Fidelity scores, readability grades
- ✅ **Debug events** - Step-by-step pipeline execution

### Viewing Traces
1. Go to https://cloud.langfuse.com (or https://us.cloud.langfuse.com)
2. View Traces tab
3. Filter by book slug
4. Click into any trace for detailed timeline

### Trace URLs in Logs
Every pipeline run logs a clickable trace URL:
```
TRACE_LINK pipeline_sync_alice-wonderland: https://cloud.langfuse.com/trace/abc123...
```

**See [`docs/implementation/LANGFUSE_IMPLEMENTATION.md`](docs/implementation/LANGFUSE_IMPLEMENTATION.md) for setup guide.**

## Troubleshooting

### API Credential Issues

If you encounter API errors, verify your credentials:

1. **OpenRouter**: Get API key from https://openrouter.ai/keys
2. **Langfuse**: Get keys from https://cloud.langfuse.com
3. **Fish Audio**: Verify API key format and subscription status at https://fish.audio

### Common Issues

- **OpenRouter authentication failed**: Check API key is valid
- **Langfuse not connecting**: Verify public/secret keys match exactly
- **Empty LLM responses**: Check Langfuse trace URL in error message for details
- **Chapter processing timeout**: Check Langfuse for latency analysis

### Debugging with Langfuse

When errors occur:
1. Look for trace URL in error message
2. Click URL to open in Langfuse dashboard
3. View exact inputs that caused failure
4. Check token usage and timing
5. Review debug events leading to error

## Acknowledgments

- Built with [LangChain](https://langchain.com/) and [LangGraph](https://langchain.com/langgraph)
- Uses [Fish Audio](https://fish.audio/) for text-to-speech
- Inspired by the need for accessible classic literature

## Dependencies

### Core Dependencies
- `langchain` - LLM framework and chains
- `langgraph` - State machine orchestration
- `pydantic` - Data validation and settings
- `fastapi` - API server
- `fish-audio-sdk` - Text-to-speech API
- `ebooklib` - EPUB generation
- `ffmpeg-python` - Audio processing

### LangChain Best Practices Dependencies
- `tiktoken` - Token counting for context management
- `langchain-community` - Caching and additional integrations
- `langfuse` - Production observability and monitoring
- `tenacity` - Advanced retry logic with exponential backoff
- `langgraph-checkpoint-sqlite` - Persistent state management

## Roadmap

### ✅ **Completed (v1.0)**
- [x] OpenRouter-only architecture (unified LLM API)
- [x] Langfuse observability integration (100% coverage)
- [x] Debug integration with trace URLs
- [x] Structured outputs with Pydantic schemas
- [x] LLM response caching for cost optimization
- [x] Fallback model configuration
- [x] Self-healing retry logic with circuit breakers
- [x] Skip completed chapters on resume
- [x] Comprehensive error tracking

### 🔄 **In Progress (v1.1)**
- [ ] Advanced cost analytics and dashboards
- [ ] Multi-chapter parallel optimization
- [ ] A/B testing framework for prompts

### 📋 **Planned (v2.0+)**
- [ ] Self-hosted TTS options
- [ ] Multi-language support
- [ ] Web dashboard for HITL review
- [ ] Integration with publishing platforms
- [ ] Kubernetes deployment guides
