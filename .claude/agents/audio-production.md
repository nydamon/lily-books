# Audio Production Agent

**Command**: `/audio-production`

## Purpose

Expert in TTS and audio mastering workflow for Lily Books audiobook production.

## Key Knowledge Areas

### 1. Fish Audio TTS ([tools/tts.py](../../src/lily_books/tools/tts.py))

**API**: Fish Audio API (https://fish.audio)

**Features**:
- High-quality neural TTS
- Custom voice cloning
- Natural prosody and emotion
- Fast processing

**Configuration**:
```bash
# .env
FISH_API_KEY=your-api-key
FISH_REFERENCE_ID=  # Optional: Custom voice model
```

**Cost**: $5-15 per 100k word book

### 2. Audio Mastering ([tools/audio.py](../../src/lily_books/tools/audio.py))

**ACX Compliance Requirements**:
- **RMS level**: -23dB to -18dB (target: -20dB)
- **Peak level**: ≤ -3dB
- **Noise floor**: ≤ -60dB
- **Format**: MP3 192kbps CBR, 44.1kHz

**Mastering Process**:
1. Normalize audio to target RMS (-20dB)
2. Apply peak limiting (-3dB max)
3. Convert WAV → MP3 (192kbps)
4. Validate ACX compliance

### 3. Pipeline Flow ([graph.py:1108-1360](../../src/lily_books/graph.py#L1108-L1360))

**Nodes** (only if `ENABLE_AUDIO=true`):
1. **tts_node** - Generate TTS audio (WAV)
2. **master_node** - ACX-compliant mastering (MP3)
3. **qa_audio_node** - Validate audio metrics
4. **package_node** - Create retail sample

**Retail Sample**: 3-minute excerpt starting at 30s mark

### 4. Audio Metadata ([models.py:168-184](../../src/lily_books/models.py#L168-L184))

```python
acx: dict = {
    "target_rms_db": -20,
    "peak_db_max": -3,
    "noise_floor_db_max": -60
}

retail_sample: dict = {
    "chapter": 1,
    "start_sec": 30,
    "duration_sec": 180  # 3 minutes
}
```

## Key Files

- [src/lily_books/tools/tts.py](../../src/lily_books/tools/tts.py) - TTS generation
- [src/lily_books/tools/audio.py](../../src/lily_books/tools/audio.py) - Mastering
- [src/lily_books/graph.py](../../src/lily_books/graph.py) - Audio nodes
- [src/lily_books/models.py](../../src/lily_books/models.py) - Audio config

## Common Questions

### Q: How do I use a custom Fish Audio voice?

**Answer**:

1. **Create voice model** at https://fish.audio:
   - Upload 1-2 minutes of voice samples
   - Train custom voice model
   - Get reference_id

2. **Configure in .env**:
```bash
FISH_REFERENCE_ID=your-custom-voice-id
```

3. **Test with single chapter**:
```bash
ENABLE_AUDIO=true python -m lily_books run 11 --slug test --chapters 1
```

### Q: Why is audio failing ACX compliance?

**Answer**:

Check metrics in QA report:

```bash
cat books/{slug}/work/qa/audio/ch01-meters.json
```

**Common Issues**:

1. **RMS too quiet** (<-23dB):
   - Increase normalization target
   - Check source audio levels

2. **RMS too loud** (>-18dB):
   - Decrease normalization target
   - Risk of clipping

3. **Peak exceeds -3dB**:
   - Apply more aggressive limiting
   - Check for sudden loud sounds

**Fix in audio.py**: Adjust mastering parameters

### Q: How much does audio cost per book?

**Answer**:

**Fish Audio Pricing** (~$0.05-0.15 per 1000 characters):

100k word book = ~500k characters
Cost = 500 × $0.10 = **$50**

**Optimization**:
- Use shorter preview samples
- Skip audio for testing (`ENABLE_AUDIO=false`)
- Batch multiple books for volume discounts

## Best Practices

### 1. Test with Single Chapter
```bash
ENABLE_AUDIO=true python -m lily_books run 11 --slug test --chapters 1
```

### 2. Validate ACX Compliance
- Check RMS, peak, noise floor
- Test retail sample extraction
- Listen for quality issues

### 3. Use Custom Voices Wisely
- Train on high-quality samples
- Test before full book production
- Consider gender/age appropriateness

### 4. Monitor Costs
- Track TTS usage per book
- Optimize for batch processing
- Consider audio-only releases

## Related Agents

- [/langgraph-pipeline](langgraph-pipeline.md) - For audio node flow
- [/testing](testing.md) - For audio testing

---

**Last Updated**: 2025-10-25
**Version**: 1.0
