"""Text-to-Speech tool using ElevenLabs API."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List
from langchain_core.tools import tool
import requests

from ..config import settings


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


def tts_elevenlabs(text: str, voice_id: str, out_wav: Path) -> Dict:
    """Synthesize text with ElevenLabs and convert to 44.1k mono WAV."""
    chunks = chunk_text(text)
    temp_files = []
    
    try:
        # Process each chunk
        for i, chunk in enumerate(chunks):
            mp3_path = out_wav.parent / f"{out_wav.stem}_chunk_{i}.mp3"
            temp_files.append(mp3_path)
            
            # Call ElevenLabs API
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "accept": "audio/mpeg",
                    "content-type": "application/json"
                },
                json={
                    "text": chunk,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                },
                timeout=300
            )
            response.raise_for_status()
            
            # Save MP3
            mp3_path.write_bytes(response.content)
        
        # Concatenate chunks if multiple
        if len(chunks) == 1:
            # Single chunk - convert directly
            subprocess.check_call([
                "ffmpeg", "-y", "-i", str(temp_files[0]),
                "-ac", "1", "-ar", "44100", "-f", "wav", str(out_wav)
            ])
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
            ])
            
            # Convert to WAV
            subprocess.check_call([
                "ffmpeg", "-y", "-i", str(concat_file),
                "-ac", "1", "-ar", "44100", "-f", "wav", str(out_wav)
            ])
            
            # Clean up concat list
            concat_list.unlink()
        
        # Get duration
        duration_result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(out_wav)
        ], capture_output=True, text=True)
        
        duration_sec = float(duration_result.stdout.strip()) if duration_result.stdout.strip() else 0.0
        
        return {
            "wav": str(out_wav),
            "duration_sec": duration_sec,
            "chunks_processed": len(chunks)
        }
        
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()


@tool
def tts_elevenlabs_tool(text: str, voice_id: str, out_wav: str) -> str:
    """Synthesize text with ElevenLabs and convert to 44.1k mono WAV.
    
    Args:
        text: Text to synthesize
        voice_id: ElevenLabs voice ID
        out_wav: Output WAV file path
    
    Returns:
        JSON string with wav path, duration, and chunks processed
    """
    result = tts_elevenlabs(text, voice_id, Path(out_wav))
    return json.dumps(result)
