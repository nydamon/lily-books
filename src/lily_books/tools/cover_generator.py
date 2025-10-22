"""Cover generation using Ideogram AI."""

import logging
from pathlib import Path

from ..models import CoverDesign, PublishingMetadata
from ..config import get_project_paths, get_config

logger = logging.getLogger(__name__)

def generate_cover_prompt(metadata: PublishingMetadata) -> str:
    """Generate Ideogram prompt for book cover."""
    
    # Style mappings
    style_prompts = {
        "classic": "elegant vintage book cover design, ornate borders, classic typography, muted earth tones, literary feel",
        "modern": "contemporary minimalist book cover, bold typography, vibrant colors, clean design",
        "minimalist": "ultra-minimalist book cover, simple geometric shapes, limited color palette, modern typography",
        "whimsical classic": "playful vintage-inspired cover, hand-drawn elements, soft pastels, charming illustrations, child-friendly",
        "academic": "scholarly book cover, clean typography, muted colors, professional layout, educational focus",
        "artistic": "creative cover design, abstract elements, artistic typography, unique color combinations, expressive",
        "nostalgic": "warm, nostalgic book cover, sepia tones, vintage photography elements, sentimental feel"
    }
    
    style = style_prompts.get(metadata.cover_style, style_prompts["classic"])
    
    prompt = f"""Professional book cover design for "{metadata.title}".

Style: {style}

Theme: Classic literature, modernized for students

Design elements:
- Title: {metadata.title}
- Author: {metadata.author}
- "Modernized Student Edition" badge or label
- Visual elements related to: {', '.join(metadata.keywords[:3])}

Requirements:
- Professional and appealing to students and educators
- Clean, readable typography
- High-quality, publishable
- No people's faces
- Suitable for both ebook and print

Art style: {style}"""
    
    return prompt


def generate_cover_with_ideogram(
    metadata: PublishingMetadata,
    slug: str,
    max_attempts: int = 3
) -> Path:
    """Generate cover using Ideogram API with validation and retry.

    Ideogram specializes in generating images with readable text, perfect for book covers.
    Includes automatic validation and retry if text rendering fails.

    Args:
        metadata: Publishing metadata with title, author, cover_prompt
        slug: Book slug for file naming
        max_attempts: Maximum number of generation attempts (default: 3)

    Returns:
        Path to validated cover image
    """
    import requests
    from ..utils.cover_validator import validate_cover_image

    config = get_config()

    if not getattr(config, "ideogram_api_key", None):
        raise ValueError(
            "Ideogram API key not configured. "
            "Set IDEOGRAM_API_KEY to enable mandatory AI cover generation."
        )

    paths = get_project_paths(slug)

    # Build rich, book-specific prompt for Ideogram
    # Ideogram excels at rendering text on images
    title_text = metadata.title
    author_text = f"by {metadata.author}"

    # Create book-specific prompt using the detailed cover_prompt from metadata
    # The cover_prompt contains time period, setting, themes, mood, and visual elements
    prompt = f"""Professional book cover design for a modernized classic literature edition.

COVER TEXT REQUIREMENTS (CRITICAL - Ideogram must render these texts clearly and prominently):
1. Main title: "{title_text}" - Large, bold, highly readable text in top half
2. Author line: "{author_text}" - Medium size, below title
3. Edition badge: "Modernized Student Edition" - Small, elegant badge at bottom

BOOK-SPECIFIC VISUAL THEME:
{metadata.cover_prompt}

DESIGN STYLE: {metadata.cover_style} aesthetic

COMPOSITION REQUIREMENTS:
- Portrait book cover format (2:3 ratio)
- Text MUST be the primary focus - large, bold, perfectly readable
- Visual elements should SUPPORT and ENHANCE the text, not compete with it
- Background and imagery should reflect the book's TIME PERIOD, SETTING, and THEMES (specified above)
- Use the suggested COLOR PALETTE from the theme description
- Create SYMBOLIC IMAGERY related to the book's content (not generic)
- Include atmospheric elements that convey the book's MOOD

TECHNICAL REQUIREMENTS:
- Professional, retail-quality design (suitable for Amazon/bookstores)
- High contrast for text readability
- No people's faces or specific characters
- Modern design sensibility appealing to students (grades 7-12) and educators
- Thematic authenticity - visuals must reflect the actual book content

The cover should immediately communicate the book's era, themes, and atmosphere while maintaining professional text clarity."""

    # Retry loop with validation
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Generating cover with Ideogram API (attempt {attempt}/{max_attempts})...")
        logger.info(f"Book-specific cover prompt: {metadata.cover_prompt}")
        logger.debug(f"Full Ideogram prompt: {prompt}")

        try:
            # Call Ideogram API
            # https://ideogram.ai/api/docs
            response = requests.post(
                "https://api.ideogram.ai/generate",
                headers={
                    "Api-Key": config.ideogram_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "image_request": {
                        "prompt": prompt,
                        "aspect_ratio": "ASPECT_2_3",  # Portrait for book cover
                        "model": "V_2",  # Latest model with best text rendering
                        "magic_prompt_option": "AUTO",  # Let Ideogram enhance the prompt
                        "style_type": "DESIGN"  # Design style for professional covers
                    }
                },
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            # Get image URL from response
            if "data" in result and len(result["data"]) > 0:
                image_url = result["data"][0]["url"]

                # Download image
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()

                # Save to deliverables
                cover_path = paths["deliverables_ebook"] / f"{slug}_cover.png"
                cover_path.write_bytes(img_response.content)

                logger.info(f"Cover generated with Ideogram: {cover_path}")

                # Validate the cover using vision API
                validation = validate_cover_image(
                    cover_path=cover_path,
                    expected_title=metadata.title,
                    expected_author=metadata.author,
                    expected_edition="Modernized Student Edition"
                )

                if validation['is_valid']:
                    logger.info(f"✓ Cover validation PASSED (attempt {attempt})")
                    return cover_path
                elif validation['should_retry'] and attempt < max_attempts:
                    logger.warning(f"✗ Cover validation FAILED (attempt {attempt}/{max_attempts}): {validation['errors']}")
                    logger.info(f"Retrying cover generation with refined prompt...")
                    # Add negative prompt feedback for next attempt
                    if 'errors' in validation and validation['errors']:
                        prompt += f"\n\nIMPORTANT: Previous attempt had these issues - avoid them:\n"
                        for error in validation['errors']:
                            prompt += f"- {error}\n"
                    continue  # Try again
                else:
                    raise RuntimeError(
                        f"Ideogram cover validation failed: {validation.get('errors') or validation.get('warnings')}"
                    )
            else:
                raise ValueError(f"No image data in Ideogram response: {result}")

        except Exception as e:
            logger.error(f"Ideogram cover generation attempt {attempt} failed: {e}")
            if attempt == max_attempts:
                raise

    # If we get here, all attempts exhausted
    raise RuntimeError("Ideogram cover generation failed after maximum retries")


def generate_cover(
    metadata: PublishingMetadata,
    slug: str
) -> CoverDesign:
    """Generate book cover using Ideogram AI."""
    cover_path = generate_cover_with_ideogram(metadata, slug)

    return CoverDesign(
        image_path=str(cover_path),
        title=metadata.title,
        subtitle=metadata.subtitle,
        author=metadata.author,
        publisher=metadata.publisher
    )
