# Lily Books

A LangChain/LangGraph pipeline for modernizing public-domain books into student-friendly English, with EPUB and audiobook generation.

## Overview

Lily Books converts 19th-century public-domain texts into modern English suitable for students, while preserving the original meaning, dialogue structure, and literary elements. The pipeline produces both EPUB ebooks and ACX-compliant audiobooks.

## Features

- **Text Modernization**: GPT-4o powered modernization with fidelity preservation
- **Quality Assurance**: Claude Sonnet 4.5 validation with local checks for quotes, emphasis, and readability
- **EPUB Generation**: Professional ebook creation with proper formatting and navigation
- **Audiobook Creation**: ElevenLabs TTS with ACX-compliant mastering
- **Human-in-the-Loop**: API endpoints for manual review and corrections
- **Cost Tracking**: Token usage monitoring and cost estimation
- **LangChain Best Practices**: Production-ready implementation with structured outputs, caching, fallback models, and advanced retry logic

## Architecture

The pipeline uses LangGraph to orchestrate the following steps:

1. **Ingest**: Load text from Gutendex API
2. **Chapterize**: Split text into chapters using regex patterns
3. **Rewrite**: Modernize paragraphs using GPT-4o with batching
4. **QA Text**: Validate modernization using Claude Sonnet 4.5 + local checks
5. **Remediate**: Retry failed paragraphs with targeted prompts
6. **EPUB Build**: Generate professional ebook with ebooklib
7. **TTS**: Synthesize audio using ElevenLabs API
8. **Master**: Apply ACX-compliant audio mastering
9. **QA Audio**: Validate audio metrics and compliance
10. **Package**: Create final deliverables and retail samples

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
# Edit .env with your API keys
```

4. Test API credentials:
```bash
# Test OpenAI
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 5}' \
     https://api.openai.com/v1/chat/completions

# Test Anthropic
curl -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "Content-Type: application/json" \
     -H "anthropic-version: 2023-06-01" \
     -d '{"model": "claude-haiku-4-5-20251001", "max_tokens": 5, "messages": [{"role": "user", "content": "Hello"}]}' \
     https://api.anthropic.com/v1/messages

# Test ElevenLabs
curl -H "xi-api-key: $ELEVENLABS_API_KEY" \
     https://api.elevenlabs.io/v1/voices
```

5. Activate the environment:
```bash
poetry shell
```

## Configuration

Create a `.env` file with the following variables:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Model configurations
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
ELEVENLABS_VOICE_ID=2EiwWnXFnvU5JabPnv8n  # Clyde voice (Rachel not available)

# Fallback models for resilience
OPENAI_FALLBACK_MODEL=gpt-4o-mini
ANTHROPIC_FALLBACK_MODEL=claude-haiku-4-5-20251001

# Caching settings
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
CACHE_TYPE=memory
REDIS_URL=redis://localhost:6379

# Langfuse observability (optional)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key_here
LANGFUSE_SECRET_KEY=your_langfuse_secret_key_here
LANGFUSE_HOST=https://cloud.langfuse.com

# Development settings
DEBUG=false
LOG_LEVEL=INFO
```

## Usage

### Command Line

Run the complete pipeline:

```python
from src.lily_books.runner import run_pipeline

result = run_pipeline("pride-prejudice", 1342)  # Gutendex book ID
print(f"Pipeline completed: {result['success']}")
```

### API Server

Start the FastAPI server:

```bash
poetry run python -m src.lily_books.api.main
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

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
- Claude Sonnet 4.5 → Claude Haiku 4.5 fallback
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
- **QA Validation**: $0.15-0.75 (Claude Sonnet 4.5) → $0.08-0.38 with caching
- **TTS**: $0.016 (ElevenLabs)
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

## Troubleshooting

### API Credential Issues

If you encounter API errors, verify your credentials:

1. **OpenAI**: Check API key format (`sk-proj-...` or `sk-...`)
2. **Anthropic**: Ensure API key starts with `sk-ant-`
3. **ElevenLabs**: Verify API key format and subscription status

### Voice Configuration

The default voice ID `2EiwWnXFnvU5JabPnv8n` (Clyde) is tested and working. To use a different voice:

1. List available voices: `curl -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v1/voices`
2. Update `ELEVENLABS_VOICE_ID` in your `.env` file
3. Test the voice: `curl -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v1/voices/{VOICE_ID}`

### Common Issues

- **ElevenLabs "voice_not_found"**: Voice ID doesn't exist in your account
- **OpenAI rate limits**: Check usage dashboard for quota status
- **Anthropic errors**: Verify model availability and API key permissions

## Acknowledgments

- Built with [LangChain](https://langchain.com/) and [LangGraph](https://langchain.com/langgraph)
- Uses [ElevenLabs](https://elevenlabs.io/) for text-to-speech
- Inspired by the need for accessible classic literature

## Dependencies

### Core Dependencies
- `langchain` - LLM framework and chains
- `langgraph` - State machine orchestration
- `pydantic` - Data validation and settings
- `fastapi` - API server
- `elevenlabs` - Text-to-speech API
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
- [x] LangChain best practices implementation
- [x] Structured outputs with Pydantic schemas
- [x] LLM response caching for cost optimization
- [x] Fallback model configuration
- [x] Advanced retry logic with tenacity
- [x] Skip completed chapters on resume
- [x] Comprehensive test suite

### 🔄 **In Progress**
- [ ] Performance optimization and benchmarking
- [ ] Enhanced error recovery strategies
- [ ] Advanced monitoring dashboards

### 📋 **Planned (v1.1+)**
- [ ] Self-hosted TTS options
- [ ] Multi-language support
- [ ] Advanced remediation strategies
- [ ] Batch processing capabilities
- [ ] Web dashboard for HITL review
- [ ] Integration with publishing platforms
- [ ] Kubernetes deployment guides
- [ ] Advanced cost analytics

