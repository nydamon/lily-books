"""Tests for tools (EPUB, TTS, audio processing)."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from lily_books.models import BookMetadata
from lily_books.tools.audio import (
    extract_retail_sample,
    get_audio_metrics,
    master_audio,
)
from lily_books.tools.epub import build_epub, escape_html
from lily_books.tools.tts import chunk_text, tts_fish_audio

sys.path.append(str(Path(__file__).parent))
from fixtures.sample_chapter import get_sample_chapter_doc


def test_escape_html():
    """Test HTML escaping and emphasis conversion."""
    text = 'He said "Hello" and _emphasized_ this word.'
    result = escape_html(text)

    assert "&quot;Hello&quot;" in result
    assert "<em>emphasized</em>" in result
    assert "&amp;" not in result  # Should not double-escape


def test_chunk_text():
    """Test text chunking for TTS."""
    short_text = "Short text"
    chunks = chunk_text(short_text, max_chars=100)

    assert len(chunks) == 1
    assert chunks[0] == short_text

    # Test long text chunking
    long_text = ". ".join([f"Sentence {i}" for i in range(100)])
    chunks = chunk_text(long_text, max_chars=200)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 200


@patch("lily_books.tools.epub.epub.write_epub")
def test_build_epub(mock_write_epub):
    """Test EPUB building with mocked ebooklib."""
    with tempfile.TemporaryDirectory() as temp_dir:
        slug = "test-book"
        chapters = [get_sample_chapter_doc()]
        metadata = BookMetadata(
            title="Test Book", author="Test Author", public_domain_source="Test Source"
        )

        # Mock the paths
        with patch("lily_books.tools.epub.get_project_paths") as mock_paths:
            mock_paths.return_value = {"deliverables_ebook": Path(temp_dir)}

            result_path = build_epub(slug, chapters, metadata)

            assert result_path.name == f"{slug}.epub"
            mock_write_epub.assert_called_once()


@patch("lily_books.tools.tts.settings")
@patch("lily_books.tools.tts.TTSRequest")
@patch("lily_books.tools.tts.Session")
@patch("lily_books.tools.tts.subprocess.check_call")
@patch("lily_books.tools.tts.subprocess.run")
def test_tts_fish_audio(
    mock_run, mock_check_call, mock_session, mock_tts_request, mock_settings
):
    """Test TTS generation with mocked Fish Audio SDK."""
    # Mock settings
    mock_settings.fish_api_key = "test_api_key"

    # Mock TTSRequest
    mock_tts_request.return_value = MagicMock()

    # Mock Fish Audio session and TTS response
    mock_tts_instance = MagicMock()
    # The tts method should return an iterable of audio chunks
    mock_tts_instance.tts.return_value = iter([b"fake mp3 content"])
    mock_session.return_value = mock_tts_instance

    # Mock ffmpeg calls
    mock_check_call.return_value = None
    mock_run.return_value = MagicMock(stdout="10.5")

    with tempfile.TemporaryDirectory() as temp_dir:
        wav_path = Path(temp_dir) / "test.wav"

        # Use longer text to pass minimum length check (10+ chars)
        result = tts_fish_audio(
            "This is a test text for TTS generation.", "test_reference_id", wav_path
        )

        assert result["wav"] == str(wav_path)
        assert result["duration_sec"] == 10.5
        assert result["chunks_processed"] == 1


@patch("lily_books.tools.audio.subprocess.check_call")
@patch("lily_books.tools.audio.subprocess.run")
def test_master_audio(mock_run, mock_check_call):
    """Test audio mastering with mocked ffmpeg."""
    mock_check_call.return_value = None
    mock_run.return_value = MagicMock(stdout="15.2")

    with tempfile.TemporaryDirectory() as temp_dir:
        input_wav = Path(temp_dir) / "input.wav"
        output_mp3 = Path(temp_dir) / "output.mp3"

        # Create dummy input file
        input_wav.write_text("dummy wav content")

        result = master_audio(input_wav, output_mp3)

        assert result["mp3"] == str(output_mp3)
        assert result["duration_sec"] == 15.2
        assert result["target_rms_db"] == -20


@patch("lily_books.tools.audio.subprocess.run")
def test_get_audio_metrics(mock_run):
    """Test audio metrics extraction with mocked ffmpeg."""
    mock_run.return_value = MagicMock(
        stderr="mean_volume: -18.5 dB\nmax_volume: -2.1 dB", stdout="12.3"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        wav_path = Path(temp_dir) / "test.wav"
        wav_path.write_text("dummy content")

        result = get_audio_metrics(wav_path)

        assert result["rms_db"] == -18.5
        assert result["peak_db"] == -2.1
        assert result["duration_sec"] == 12.3
        assert result["file_path"] == str(wav_path)


@patch("lily_books.tools.audio.subprocess.check_call")
def test_extract_retail_sample(mock_check_call):
    """Test retail sample extraction with mocked ffmpeg."""
    mock_check_call.return_value = None

    with tempfile.TemporaryDirectory() as temp_dir:
        input_mp3 = Path(temp_dir) / "input.mp3"
        output_sample = Path(temp_dir) / "sample.mp3"

        # Create dummy input file
        input_mp3.write_text("dummy mp3 content")

        result = extract_retail_sample(input_mp3, 30, 180, output_sample)

        assert result["sample_path"] == str(output_sample)
        assert result["start_sec"] == 30
        assert result["duration_sec"] == 180
        assert result["source_chapter"] == str(input_mp3)


def test_tool_error_handling():
    """Test error handling in tools."""
    # Test TTS with missing SDK - should raise RuntimeError
    with tempfile.TemporaryDirectory() as temp_dir:
        wav_path = Path(temp_dir) / "test.wav"

        with patch("lily_books.tools.tts.Session", None):
            with patch("lily_books.tools.tts.TTSRequest", None):
                with pytest.raises(RuntimeError, match="Fish Audio SDK not installed"):
                    tts_fish_audio(
                        "This is a test text for error handling.",
                        "invalid_reference",
                        wav_path,
                    )

    # Test TTS with text too short - should raise ValueError
    # Mock the SDK to test validation
    with tempfile.TemporaryDirectory() as temp_dir:
        wav_path = Path(temp_dir) / "test.wav"

        with patch("lily_books.tools.tts.Session", MagicMock()):
            with patch("lily_books.tools.tts.TTSRequest", MagicMock()):
                with pytest.raises(ValueError, match="Text too short for TTS"):
                    tts_fish_audio("Short", "reference", wav_path)

    # Test audio mastering with missing input file
    with tempfile.TemporaryDirectory() as temp_dir:
        input_wav = Path(temp_dir) / "missing.wav"
        output_mp3 = Path(temp_dir) / "output.mp3"

        with pytest.raises(RuntimeError):
            master_audio(input_wav, output_mp3)
