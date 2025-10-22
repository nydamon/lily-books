# Cover Generation Fix - DALL-E Integration

**Date**: 2025-01-20
**Issue**: Cover generation failing due to OpenRouter API limitation

---

## Problem Summary

When `USE_AI_COVERS=true` was enabled, the pipeline generated template covers instead of AI-generated covers. Investigation revealed two issues:

### Issue 1: DALL-E Not Available via OpenRouter ⚠️ CRITICAL

**Error**: `Error code: 405 - DALL-E cover generation failed`

**Root Cause**: The cover generator was trying to use DALL-E 3 through OpenRouter:
```python
client = OpenAI(
    api_key=config.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1"  # ❌ DALL-E not supported here
)
```

**Explanation**: OpenRouter only supports **text generation models** (Claude, GPT-4, etc.). It does **NOT** support **image generation models** like DALL-E 3, DALL-E 2, or Stable Diffusion.

### Issue 2: Metadata Generation Pars Parsing Error (Separate Bug)

**Error**: `Failed to parse PublishingMetadata - 5 validation errors`

**Root Cause**: LLM returning wrapped structure instead of direct properties:
```json
{
  "description": "Extended metadata...",
  "properties": {
    "title": "...",
    "author": "..."
  }
}
```

**Expected**:
```json
{
  "title": "...",
  "author": "..."
}
```

This is a known issue from the previous session (documented in [FIXES_APPLIED.md](FIXES_APPLIED.md) as item #18 in "Remaining Known Issues").

---

## ✅ Fix Applied

### Modified File: [src/lily_books/tools/cover_generator.py](src/lily_books/tools/cover_generator.py)

**Lines 54-73**: Changed DALL-E to use direct OpenAI API

```python
def generate_cover_with_dalle(
    metadata: PublishingMetadata,
    slug: str
) -> Path:
    """Generate cover using DALL-E 3 via direct OpenAI API.

    Note: DALL-E is NOT available via OpenRouter - must use direct OpenAI API.
    """
    from openai import OpenAI

    config = get_config()

    # DALL-E requires direct OpenAI API (not OpenRouter)
    # Check if we have OpenAI API key
    if not hasattr(config, 'openai_api_key') or not config.openai_api_key:
        logger.warning("No OpenAI API key configured - DALL-E requires direct OpenAI access")
        return generate_cover_template(metadata, slug)

    client = OpenAI(api_key=config.openai_api_key)  # ✅ Direct API
    paths = get_project_paths(slug)
    # ... rest of function unchanged
```

**Key Changes**:
1. ✅ Removed OpenRouter base_url
2. ✅ Added check for `openai_api_key` existence
3. ✅ Falls back to template if no OpenAI key configured
4. ✅ Updated docstring to clarify API routing
5. ✅ Added helpful warning message when OpenAI key missing

---

## 📝 Documentation Updates

### Modified File: [env.example](env.example)

**Lines 2-4**: Added clarifying comments

```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key_here  # Required for DALL-E cover generation (direct OpenAI API)
OPENROUTER_API_KEY=your_openrouter_api_key_here  # Required for text generation (Claude, GPT-4o-mini)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here  # Required for audio narration
```

**Line 33**: Updated USE_AI_COVERS comment

```bash
USE_AI_COVERS=false  # Set to true to use DALL-E 3 for AI-generated covers (requires OPENAI_API_KEY)
```

---

## 🔧 How to Use AI Covers

### Requirements:
1. **OpenAI API Key** (separate from OpenRouter)
   - Sign up at https://platform.openai.com/
   - Generate API key in your dashboard
   - Add to `.env` as `OPENAI_API_KEY=sk-...`

2. **Environment Configuration**:
```bash
# In your .env file:
OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here  # Direct OpenAI
OPENROUTER_API_KEY=sk-or-your-openrouter-key  # For text models
USE_AI_COVERS=true  # Enable DALL-E
```

### Cost Considerations:

DALL-E 3 pricing (as of 2025):
- **Standard quality** (1024x1024): $0.040 per image
- **HD quality** (1024x1792): $0.080 per image

Current implementation uses **HD quality at 1024x1792** (portrait orientation suitable for book covers).

**Cost per book**: ~$0.08 per cover image

### Fallback Behavior:

The cover generator has automatic fallback:
1. **First**: Try DALL-E 3 via OpenAI (if `USE_AI_COVERS=true` and `OPENAI_API_KEY` exists)
2. **Fallback**: Use PIL template cover (always works, no API needed)

**Template covers**:
- Solid color background (#2c3e50 dark blue)
- Title and author text (centered, white)
- "Modernized Student Edition" badge
- 1600x2400 resolution
- Good for testing, not production

---

## ✅ Current Status

### What Works:
- ✅ Cover generator correctly routes to direct OpenAI API
- ✅ Fallback to template cover if OpenAI key missing
- ✅ Clear error messages and logging
- ✅ Documentation updated in env.example

### What Doesn't Work Yet:
- ⚠️ **Metadata generation bug** prevents pipeline from reaching cover node
- ⚠️ Need to fix metadata parser before testing DALL-E integration

### Next Steps:
1. **Fix metadata generation bug** (known issue #18 from previous session)
2. **Add OpenAI API key** to `.env` (if you want AI covers)
3. **Test DALL-E integration** end-to-end
4. **Optionally**: Add image quality/size config options

---

## 🎨 DALL-E Prompt Design

The cover generator creates prompts based on:
- Book title and author
- Cover style (modern, classic, minimalist, etc.)
- Keywords from metadata
- Target audience (students, educators)

**Example prompt** for Pride & Prejudice:
```
Professional book cover design for "Pride and Prejudice (Modernized Student Edition)".

Style: contemporary minimalist book cover, bold typography, vibrant colors, clean design

Theme: Classic literature, modernized for students

Design elements:
- Title: Pride and Prejudice
- Author: Jane Austen
- "Modernized Student Edition" badge or label
- Visual elements related to: social class, marriage, romance

Requirements:
- Professional and appealing to students and educators
- Clean, readable typography
- High-quality, publishable
- No people's faces
- Suitable for both ebook and print

Art style: contemporary minimalist book cover, bold typography, vibrant colors, clean design
```

---

## 📊 API Routing Summary

| Service | API Provider | Purpose | Config Variable |
|---------|-------------|---------|-----------------|
| **Text Generation** (GPT-4o-mini, Claude) | OpenRouter | Chapter rewriting, QA, metadata | `OPENROUTER_API_KEY` |
| **Image Generation** (DALL-E 3) | OpenAI Direct | Cover generation | `OPENAI_API_KEY` |
| **Audio Generation** (TTS) | ElevenLabs | Narration | `ELEVENLABS_API_KEY` |

**Why different providers?**
- OpenRouter aggregates text models but doesn't support image generation
- DALL-E is exclusive to OpenAI's direct API
- ElevenLabs specializes in voice synthesis

---

## 🐛 Known Limitations

1. **No Stable Diffusion support**: Only DALL-E 3 currently supported
2. **Fixed image size**: Hardcoded to 1024x1792 (HD portrait)
3. **No prompt customization**: Users can't override DALL-E prompts via API
4. **No image editing**: Can't regenerate variations or edit existing covers
5. **Metadata bug blocks testing**: Need to fix parser before full E2E test

---

**Fix Status**: ✅ DALL-E routing fixed, pending metadata bug resolution for full test
**Files Modified**: 2 (cover_generator.py, env.example)
**Breaking Changes**: None (backward compatible fallback)
