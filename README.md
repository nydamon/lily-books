# Lily Books

A LangChain/LangGraph pipeline for modernizing public-domain books into student-friendly English, with EPUB and audiobook generation.

## Overview

Lily Books converts 19th-century public-domain texts into modern English suitable for students, while preserving the original meaning, dialogue structure, and literary elements. The pipeline produces both EPUB ebooks and ACX-compliant audiobooks.

## Claude Code Agent System 🤖

This project includes a comprehensive subject-matter expert agent system for Claude Code. Use slash commands to activate specialized agents:

- `/langgraph-pipeline` - State machine architecture expert
- `/llm-chains` - LLM optimization and cost management expert
- `/publishing` - Publishing and distribution expert (PublishDrive-focused)
- `/qa-validation` - Quality assurance and validation expert
- `/testing` - Testing and reliability expert
- `/audio-production` - TTS and audio mastering expert
- `/epub-covers` - EPUB and cover generation expert

**Learn more**: See [claude.md](claude.md) for complete agent documentation.

## Features

### Core Pipeline
- **Text Modernization**: GPT-4o-mini powered modernization with fidelity preservation via OpenRouter
- **Quality Assurance**: Claude 4.5 Haiku validation with comprehensive quality checks
- **EPUB Generation**: Professional ebook creation with proper formatting and navigation
- **Audiobook Creation**: Fish Audio TTS with ACX-compliant mastering
- **AI Cover Generation**: Ideogram AI cover generation with automated validation

### Publishing & Distribution (NEW)
- **Free Distribution Channels**: Automated distribution to Amazon KDP, Google Play Books, and Draft2Digital
- **Free Identifiers**: Automatic assignment of ASIN (Amazon), Google ID, and ISBN (Draft2Digital)
- **Multi-Edition Support**: Generates Kindle + Universal editions for maximum reach
- **SEO Metadata**: AI-generated descriptions, keywords, and BISAC categories
- **Wide Distribution**: 400+ stores via Draft2Digital (Apple Books, Kobo, Barnes & Noble, Scribd, OverDrive, etc.)
- **Draft2Digital Integration**: Fully automated API upload with free ISBN assignment
- **Validation Gates**: EPUB and metadata validation before upload
- **Publishing Dashboard**: Status tracking and reporting

### Production Features
- **Langfuse Observability**: Complete tracing, cost tracking, and performance monitoring
- **Debug Integration**: Trace IDs in logs, clickable trace URLs in errors
- **OpenRouter Architecture**: Single API for all LLM operations with unified billing
- **Production-Ready**: Structured outputs, caching, fallback models, and self-healing retry logic

## Architecture

The pipeline uses LangGraph to orchestrate the following steps:

### Core Pipeline
1. **Ingest**: Load text from Project Gutenberg via Gutendex API
2. **Chapterize**: Split text into chapters with smart detection
3. **Rewrite**: Modernize text using GPT-4o-mini (via OpenRouter) with parallel batching
4. **QA Text**: Validate quality using Claude 4.5 Haiku (via OpenRouter) *(optional)*
5. **Remediate**: Retry failed chapters with enhanced prompts *(optional)*
6. **Metadata**: Generate publishing metadata and descriptions
7. **Cover**: Generate Ideogram AI book cover with automated validation
8. **EPUB**: Build professional ebook with ebooklib

### Audio Pipeline *(optional)*
9. **TTS**: Synthesize audio using Fish Audio API
10. **Master**: Apply ACX-compliant audio mastering
11. **QA Audio**: Validate audio metrics and compliance
12. **Package**: Create final deliverables and retail samples

### Publishing Pipeline *(optional)*
13. **Assign Identifiers**: Assign free ASIN, Google ID, and ISBN
14. **Prepare Editions**: Create Kindle + Universal edition EPUBs
15. **Generate Retail Metadata**: AI-powered SEO metadata generation
16. **Calculate Pricing**: Optimize pricing for 70% Amazon royalty tier
17. **Validate Metadata**: Check retailer requirements
18. **Validate EPUB**: Run epubcheck validation
19. **Human Review**: Manual approval gate (optional)
20. **Upload Amazon**: Upload to Amazon KDP *(manual with instructions)*
21. **Upload Google**: Upload to Google Play Books *(manual with instructions)*
22. **Upload Draft2Digital**: **Fully automated upload** to 400+ stores
23. **Publishing Report**: Generate status report and dashboard

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

**Publishing & Distribution (`ENABLE_PUBLISHING`)**
- When `true`: Runs full publishing pipeline with automated Draft2Digital upload
- When `false` (default): Skips publishing steps
- Use case: Enable for automated distribution to 400+ ebook retailers
- **See `PUBLISHING_GUIDE.md` for detailed setup instructions**

**Example Configurations:**
```bash
# Ebook only, no QA (fastest)
ENABLE_QA_REVIEW=false
ENABLE_AUDIO=false
ENABLE_PUBLISHING=false

# Ebook + Publishing (automated distribution)
ENABLE_QA_REVIEW=true
ENABLE_AUDIO=false
ENABLE_PUBLISHING=true
TARGET_RETAILERS=draft2digital

# Full production pipeline (ebook + audio + publishing)
ENABLE_QA_REVIEW=true
ENABLE_AUDIO=true
ENABLE_PUBLISHING=true
TARGET_RETAILERS=amazon,google,draft2digital
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

# Publishing & Distribution (optional)
ENABLE_PUBLISHING=false  # Enable/disable publishing pipeline
TARGET_RETAILERS=draft2digital  # Comma-separated: amazon,google,draft2digital
DEFAULT_PRICE_USD=2.99  # Default ebook price
ENABLE_HUMAN_REVIEW=true  # Require manual approval before upload

# Retailer API Keys (optional)
DRAFT2DIGITAL_API_KEY=  # For automated Draft2Digital upload
# GOOGLE_PLAY_CREDENTIALS_PATH=  # Path to Google service account JSON
# KDP_EMAIL=  # Amazon KDP email
# KDP_PASSWORD=  # Amazon KDP password
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

# Full book with publishing (automated upload to Draft2Digital)
ENABLE_PUBLISHING=true python3 -m lily_books run 1342 --slug pride-and-prejudice

# Check status
python3 -m lily_books status alice-wonderland
```

### Publishing & Distribution

To enable automated distribution to 400+ ebook retailers:

```bash
# 1. Get Draft2Digital API key from https://draft2digital.com/settings/api
# 2. Add to .env:
echo "ENABLE_PUBLISHING=true" >> .env
echo "TARGET_RETAILERS=draft2digital" >> .env
echo "DRAFT2DIGITAL_API_KEY=your-key-here" >> .env

# 3. Run pipeline (uploads automatically)
python3 -m lily_books run 1342 --slug pride-and-prejudice

# Result:
# ✅ Book uploaded to Draft2Digital
# 📖 Free ISBN assigned
# 🔗 Universal book link generated
# 📦 Distributed to Apple Books, Kobo, B&N, Scribd, OverDrive, etc.
```

**See detailed guides:**
- **`PUBLISHING_GUIDE.md`** - Complete publishing documentation
- **`DRAFT2DIGITAL_QUICKSTART.md`** - 5-minute Draft2Digital setup
- **`PUBLISHING_IMPLEMENTATION.md`** - Technical implementation status

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

### Production Costs (per book, ~100k words)

- **Modernization**: $2.50-5.50 (GPT-4o-mini via OpenRouter)
- **QA Validation**: $0.50-2.00 (Claude 4.5 Haiku via OpenRouter)
- **TTS Audio**: $5.00-15.00 (Fish Audio)
- **Cover Generation**: $0.04 (DALL-E 3)
- **Total**: **$7.54-$20.54 per book**

### Distribution Costs

- **Draft2Digital**: **$0** (free)
- **ISBN**: **$0** (free from Draft2Digital)
- **Amazon KDP**: **$0** (free ASIN)
- **Google Play Books**: **$0** (free Google ID)
- **Total Distribution**: **$0**

### Revenue & ROI

**Example: $2.99 ebook**
- Draft2Digital (Apple Books): $1.88 per sale (63% of list price)
- Amazon KDP (70% royalty): $2.09 per sale
- Google Play Books: $1.55 per sale (52% of list price)

**Break-even**: 3-8 sales at $2.99
**Year 1 projection**: $1,400-$5,000 revenue per book
**ROI**: 300-1,000%+ within 12 months

**Cost Reduction**: 30-50% savings through LLM caching and adaptive batching

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

### ✅ **Publishing Features (v1.5)**
- [x] Free distribution infrastructure (Phase 1)
- [x] Draft2Digital API integration (Phase 2)
- [x] Multi-edition support (Kindle + Universal)
- [x] AI-powered SEO metadata generation
- [x] Free ISBN assignment
- [x] Distribution to 400+ stores
- [ ] Google Play Books API integration (Phase 3)
- [ ] Amazon KDP automation (Phase 4 - optional)

### 🔄 **In Progress (v2.0)**
- [ ] Batch processing for multiple books
- [ ] Sales analytics aggregation
- [ ] A/B metadata testing
- [ ] Advanced cost analytics dashboards
- [ ] Multi-chapter parallel optimization

### 📋 **Planned (v2.5+)**
- [ ] Self-hosted TTS options
- [ ] Multi-language support
- [ ] Web dashboard for HITL review
- [ ] Dynamic pricing based on sales data
- [ ] Kubernetes deployment guides
