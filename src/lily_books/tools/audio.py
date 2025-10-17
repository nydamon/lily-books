"""Audio processing tools for mastering and QA."""

import json
import subprocess
from pathlib import Path
from typing import Dict
from langchain_core.tools import tool


def master_audio(input_wav: Path, output_mp3: Path, target_rms_db: float = -20) -> Dict:
    """Master audio using ffmpeg ACX-compliant chain."""
    try:
        # ACX mastering chain: highpass → lowpass → loudnorm → pad → MP3 CBR 192k
        subprocess.check_call([
            "ffmpeg", "-y", "-i", str(input_wav),
            "-af", f"highpass=f=80,lowpass=f=8000,loudnorm=I={target_rms_db}:TP=-3:LRA=11",
            "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
            str(output_mp3)
        ])
        
        # Get duration
        duration_result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(output_mp3)
        ], capture_output=True, text=True)
        
        duration_sec = float(duration_result.stdout.strip()) if duration_result.stdout.strip() else 0.0
        
        return {
            "mp3": str(output_mp3),
            "duration_sec": duration_sec,
            "target_rms_db": target_rms_db
        }
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Audio mastering failed: {e}")


def get_audio_metrics(wav_path: Path) -> Dict:
    """Get audio metrics using ffmpeg volumedetect."""
    try:
        # Run volumedetect
        result = subprocess.run([
            "ffmpeg", "-i", str(wav_path), "-af", "volumedetect",
            "-f", "null", "-"
        ], capture_output=True, text=True)
        
        # Parse output for metrics
        rms_db = None
        peak_db = None
        duration_sec = None
        
        for line in result.stderr.split('\n'):
            if 'mean_volume:' in line:
                try:
                    rms_db = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                except (ValueError, IndexError):
                    pass
            elif 'max_volume:' in line:
                try:
                    peak_db = float(line.split('max_volume:')[1].split('dB')[0].strip())
                except (ValueError, IndexError):
                    pass
        
        # Get duration separately
        duration_result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(wav_path)
        ], capture_output=True, text=True)
        
        if duration_result.stdout.strip():
            duration_sec = float(duration_result.stdout.strip())
        
        return {
            "rms_db": rms_db,
            "peak_db": peak_db,
            "duration_sec": duration_sec,
            "file_path": str(wav_path)
        }
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Audio metrics extraction failed: {e}")


def extract_retail_sample(chapter_mp3: Path, start_sec: int, duration_sec: int, output: Path) -> Dict:
    """Extract retail sample from mastered chapter audio."""
    try:
        subprocess.check_call([
            "ffmpeg", "-y", "-i", str(chapter_mp3),
            "-ss", str(start_sec), "-t", str(duration_sec),
            "-c", "copy", str(output)
        ])
        
        return {
            "sample_path": str(output),
            "start_sec": start_sec,
            "duration_sec": duration_sec,
            "source_chapter": str(chapter_mp3)
        }
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Retail sample extraction failed: {e}")


@tool
def master_audio_tool(input_wav: str, output_mp3: str, target_rms_db: float = -20) -> str:
    """Master audio using ffmpeg ACX-compliant chain.
    
    Args:
        input_wav: Input WAV file path
        output_mp3: Output MP3 file path
        target_rms_db: Target RMS level in dB
    
    Returns:
        JSON string with mp3 path, duration, and target RMS
    """
    result = master_audio(Path(input_wav), Path(output_mp3), target_rms_db)
    return json.dumps(result)


@tool
def get_audio_metrics_tool(wav_path: str) -> str:
    """Get audio metrics using ffmpeg volumedetect.
    
    Args:
        wav_path: WAV file path to analyze
    
    Returns:
        JSON string with RMS, peak, duration metrics
    """
    result = get_audio_metrics(Path(wav_path))
    return json.dumps(result)


@tool
def extract_retail_sample_tool(chapter_mp3: str, start_sec: int, duration_sec: int, output: str) -> str:
    """Extract retail sample from mastered chapter audio.
    
    Args:
        chapter_mp3: Source chapter MP3 file path
        start_sec: Start time in seconds
        duration_sec: Duration in seconds
        output: Output sample file path
    
    Returns:
        JSON string with sample path and timing info
    """
    result = extract_retail_sample(Path(chapter_mp3), start_sec, duration_sec, Path(output))
    return json.dumps(result)

