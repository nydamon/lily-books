"""Text-to-Speech tool using Fish Audio API."""

import json
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List
from langchain_core.tools import tool
try:
    from fish_audio_sdk import Session, TTSRequest
except ImportError:  # pragma: no cover - optional dependency
    Session = None  # type: ignore[assignment]
    TTSRequest = None  # type: ignore[assignment]

from ..config import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_chars: int = 200000) -> List[str]:
    """Split text into chunks suitable for TTS API."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = text.split('. ')
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk + sentence + '. ') <= max_chars:
            current_chunk += sentence + '. '
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + '. '

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def tts_fish_audio(text: str, reference_id: str, out_wav: Path) -> Dict:
    """Synthesize text with Fish Audio and convert to 44.1k mono WAV.

    Args:
        text: Text to synthesize
        reference_id: Fish Audio voice model ID (optional, uses default if empty)
        out_wav: Output WAV file path

    Returns:
        Dict with wav path, duration, and chunks processed

    Raises:
        ValueError: If text validation fails or API key is missing
        RuntimeError: If Fish Audio SDK is not available
    """
    if Session is None or TTSRequest is None:
        raise RuntimeError(
            "Fish Audio SDK not installed. Install with: poetry add fish-audio-sdk"
        )

    # Basic sanity checks
    if not text or len(text.strip()) < 10:
        raise ValueError(f"Text too short for TTS: {len(text)} chars (minimum 10)")

    if len(text) > 1_000_000:  # 1MB limit
        raise ValueError(f"Text too long for TTS: {len(text)} chars (maximum 1,000,000)")

    # Check for problematic characters
    if not any(char.isalpha() for char in text[:100]):
        raise ValueError("Text lacks readable content (no alphabetic characters)")

    chunks = chunk_text(text)
    temp_files = []

    try:
        if not settings.fish_api_key:
            raise ValueError(
                "Fish Audio API key not configured. "
                "Set FISH_API_KEY or disable ENABLE_AUDIO."
            )

        # Initialize Fish Audio session
        session = Session(settings.fish_api_key)

        # Process each chunk
        for i, chunk in enumerate(chunks):
            mp3_path = out_wav.parent / f"{out_wav.stem}_chunk_{i}.mp3"
            temp_files.append(mp3_path)

            # Prepare TTS request
            tts_request = TTSRequest(
                text=chunk,
                reference_id=reference_id if reference_id else None
            )

            # Call Fish Audio API and save MP3
            with open(mp3_path, "wb") as f:
                for audio_chunk in session.tts(tts_request):
                    f.write(audio_chunk)

            logger.info(f"Generated audio chunk {i+1}/{len(chunks)}: {mp3_path}")

        # Concatenate chunks if multiple
        if len(chunks) == 1:
            # Single chunk - convert directly
            subprocess.check_call([
                "ffmpeg", "-y", "-i", str(temp_files[0]),
                "-ac", "1", "-ar", "44100", "-f", "wav", str(out_wav)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Multiple chunks - concatenate first, then convert
            concat_file = out_wav.parent / f"{out_wav.stem}_concat.mp3"
            temp_files.append(concat_file)

            # Create concat list
            concat_list = out_wav.parent / "concat_list.txt"
            with open(concat_list, 'w') as f:
                for temp_file in temp_files[:-1]:  # Exclude concat_file itself
                    f.write(f"file '{temp_file.absolute()}'\n")

            # Concatenate MP3s
            subprocess.check_call([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c", "copy", str(concat_file)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Convert to WAV
            subprocess.check_call([
                "ffmpeg", "-y", "-i", str(concat_file),
                "-ac", "1", "-ar", "44100", "-f", "wav", str(out_wav)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Clean up concat list
            concat_list.unlink()

        # Get duration
        duration_result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(out_wav)
        ], capture_output=True, text=True)

        duration_sec = float(duration_result.stdout.strip()) if duration_result.stdout.strip() else 0.0

        logger.info(f"Generated audio: {out_wav} ({duration_sec:.2f}s)")

        return {
            "wav": str(out_wav),
            "duration_sec": duration_sec,
            "chunks_processed": len(chunks)
        }

    except Exception as e:
        logger.error(f"Fish Audio TTS failed: {e}")
        raise

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()


@tool
def tts_fish_audio_tool(text: str, reference_id: str, out_wav: str) -> str:
    """Synthesize text with Fish Audio and convert to 44.1k mono WAV.

    Args:
        text: Text to synthesize
        reference_id: Fish Audio voice model ID (optional)
        out_wav: Output WAV file path

    Returns:
        JSON string with wav path, duration, and chunks processed
    """
    result = tts_fish_audio(text, reference_id, Path(out_wav))
    return json.dumps(result)
