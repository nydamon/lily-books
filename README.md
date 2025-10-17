# Lily Books

A LangChain/LangGraph pipeline for modernizing public-domain books into student-friendly English, with EPUB and audiobook generation.

## Overview

Lily Books converts 19th-century public-domain texts into modern English suitable for students, while preserving the original meaning, dialogue structure, and literary elements. The pipeline produces both EPUB ebooks and ACX-compliant audiobooks.

## Features

- **Text Modernization**: GPT-4o powered modernization with fidelity preservation
- **Quality Assurance**: Claude Sonnet validation with local checks for quotes, emphasis, and readability
- **EPUB Generation**: Professional ebook creation with proper formatting and navigation
- **Audiobook Creation**: ElevenLabs TTS with ACX-compliant mastering
- **Human-in-the-Loop**: API endpoints for manual review and corrections
- **Cost Tracking**: Token usage monitoring and cost estimation

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

4. Activate the environment:
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

# Optional: Custom model configurations
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
ELEVENLABS_VOICE_ID=Rachel

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

## Cost Estimation

Approximate costs per 1,000 words:

- **Modernization**: $0.50-2.00 (GPT-4o)
- **QA Validation**: $0.15-0.75 (Claude Sonnet)
- **TTS**: $0.016 (ElevenLabs)
- **Total**: $0.67-2.77 per 1,000 words

## Development

### Running Tests

```bash
poetry run pytest
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

## Acknowledgments

- Built with [LangChain](https://langchain.com/) and [LangGraph](https://langchain.com/langgraph)
- Uses [ElevenLabs](https://elevenlabs.io/) for text-to-speech
- Inspired by the need for accessible classic literature

## Roadmap

- [ ] Self-hosted TTS options
- [ ] Multi-language support
- [ ] Advanced remediation strategies
- [ ] Batch processing capabilities
- [ ] Web dashboard for HITL review
- [ ] Integration with publishing platforms

