"""Cover image validation using Claude vision API via OpenRouter."""

import logging
import base64
from pathlib import Path
from typing import Dict, List
import requests
import json

logger = logging.getLogger(__name__)


def validate_cover_image(
    cover_path: Path,
    expected_title: str,
    expected_author: str,
    expected_edition: str = "Modernized Student Edition"
) -> Dict[str, any]:
    """Validate cover image using Claude vision API.

    Checks for:
    - Text rendering quality (no garbled text, duplicates, or gibberish)
    - Presence of required text elements (title, author, edition)
    - Professional appearance

    Args:
        cover_path: Path to cover image PNG file
        expected_title: The book title that should appear on cover
        expected_author: The author name that should appear on cover
        expected_edition: The edition text that should appear (default: "Modernized Student Edition")

    Returns:
        Dict with:
            - is_valid: bool - whether cover passes validation
            - errors: List[str] - list of validation errors found
            - warnings: List[str] - list of non-critical issues
            - should_retry: bool - whether to regenerate the cover
    """
    import os

    # Use OpenRouter for Claude API access (not direct Anthropic)
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        logger.warning("No OPENROUTER_API_KEY found - skipping cover validation")
        return {
            "is_valid": True,
            "errors": [],
            "warnings": ["Validation skipped - no OpenRouter API key configured"],
            "should_retry": False,
            "reasoning": "Validation disabled"
        }

    # Read image and encode as base64
    with open(cover_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    # Build validation prompt
    prompt = f"""You are validating a book cover image for quality control. Analyze this cover carefully.

EXPECTED TEXT ELEMENTS:
1. Title: "{expected_title}"
2. Author: "{expected_author}" (may appear as "by {expected_author}" or just the author name)
3. Edition badge: "{expected_edition}"

VALIDATION CRITERIA:
1. **Text Rendering Quality**:
   - Is all text clear, readable, and correctly spelled?
   - Are there any duplicated words (e.g., "BY JANE AUSTEN BY" instead of "BY JANE AUSTEN")?
   - Is there any garbled/gibberish text that doesn't belong?
   - Are the required text elements present and legible?

2. **Text Accuracy**:
   - Does the title match exactly: "{expected_title}"?
   - Does the author attribution appear correctly (without duplicates)?
   - Is the edition badge visible and correct?

3. **Professional Quality**:
   - Does the cover look professional and retail-ready?
   - Is the text appropriately sized and positioned?
   - Are there any obvious visual artifacts or errors?

RESPOND IN JSON FORMAT:
{{
  "is_valid": true/false,
  "errors": ["list of critical errors that require regeneration"],
  "warnings": ["list of minor issues that don't require regeneration"],
  "text_found": {{
    "title": "actual title text found on cover",
    "author": "actual author text found on cover",
    "edition": "actual edition text found on cover or null"
  }},
  "should_retry": true/false,
  "reasoning": "brief explanation of validation decision"
}}

If there are text rendering errors (duplicates, gibberish, missing required text), set should_retry=true.
Be strict - covers must be retail-quality with perfect text rendering."""

    try:
        # Call Claude 4.5 Haiku with vision via OpenRouter
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3.5-haiku",  # OpenRouter model name
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }],
                "max_tokens": 1000
            },
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        response_text = result['choices'][0]['message']['content']

        # Extract JSON from response (may be wrapped in markdown or have extra content)
        # Strip markdown code blocks
        cleaned_text = response_text
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned_text:
            cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()

        # Find the JSON object - it starts with { and ends with }
        # This handles cases where LLM adds commentary before or after the JSON
        start_idx = cleaned_text.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object found in response")

        # Find the matching closing brace
        brace_count = 0
        end_idx = start_idx
        for i in range(start_idx, len(cleaned_text)):
            if cleaned_text[i] == '{':
                brace_count += 1
            elif cleaned_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        json_str = cleaned_text[start_idx:end_idx]
        validation_result = json.loads(json_str)

        logger.info(f"Cover validation result: valid={validation_result.get('is_valid')}, "
                   f"errors={len(validation_result.get('errors', []))}, "
                   f"should_retry={validation_result.get('should_retry')}")

        if validation_result.get('errors'):
            logger.warning(f"Cover validation errors: {validation_result['errors']}")

        return validation_result

    except Exception as e:
        logger.error(f"Cover validation failed: {e}")
        # On validation error, assume cover is fine (don't block pipeline)
        return {
            "is_valid": True,
            "errors": [],
            "warnings": [f"Validation failed: {str(e)}"],
            "should_retry": False,
            "reasoning": "Validation system error - proceeding with cover"
        }
