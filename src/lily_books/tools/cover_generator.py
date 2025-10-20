"""Cover generation using AI or templates."""

import logging
import base64
from pathlib import Path
from typing import Optional
from io import BytesIO

from ..models import CoverDesign, PublishingMetadata
from ..config import get_project_paths, get_config

logger = logging.getLogger(__name__)

def generate_cover_prompt(metadata: PublishingMetadata) -> str:
    """Generate DALL-E prompt for book cover."""
    
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


def generate_cover_with_dalle(
    metadata: PublishingMetadata,
    slug: str
) -> Path:
    """Generate cover using DALL-E 3."""
    from openai import OpenAI
    
    config = get_config()
    client = OpenAI(api_key=config.openai_api_key)
    paths = get_project_paths(slug)
    
    # Generate prompt
    prompt = metadata.cover_prompt or generate_cover_prompt(metadata)
    
    logger.info(f"Generating cover with DALL-E 3...")
    logger.debug(f"Prompt: {prompt}")
    
    try:
        # Call DALL-E 3
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1792",  # Closest to 1600x2400 ratio
            quality="hd",
            n=1
        )
        
        # Download image
        image_url = response.data[0].url
        
        import requests
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        
        # Save to deliverables
        cover_path = paths["deliverables_ebook"] / f"{slug}_cover.png"
        cover_path.write_bytes(img_response.content)
        
        logger.info(f"Cover generated: {cover_path}")
        return cover_path
        
    except Exception as e:
        logger.error(f"DALL-E cover generation failed: {e}")
        # Fallback to template
        return generate_cover_template(metadata, slug)


def generate_cover_template(
    metadata: PublishingMetadata,
    slug: str
) -> Path:
    """Generate cover using PIL template (fallback)."""
    from PIL import Image, ImageDraw, ImageFont
    
    paths = get_project_paths(slug)
    
    # Create blank cover
    width, height = 1600, 2400
    img = Image.new('RGB', (width, height), color='#2c3e50')
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to load a nice font
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 80)
        author_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 50)
        badge_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 35)
    except:
        # Fallback to default
        title_font = ImageFont.load_default()
        author_font = ImageFont.load_default()
        badge_font = ImageFont.load_default()
    
    # Draw title (wrapped)
    title_words = metadata.title.split()
    title_lines = []
    current_line = ""
    
    for word in title_words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=title_font)
        if bbox[2] - bbox[0] < width - 200:
            current_line = test_line
        else:
            if current_line:
                title_lines.append(current_line)
            current_line = word
    
    if current_line:
        title_lines.append(current_line)
    
    # Draw centered title
    y_offset = height // 3
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, y_offset), line, fill='#ecf0f1', font=title_font)
        y_offset += 100
    
    # Draw author
    author_text = f"by {metadata.author}"
    bbox = draw.textbbox((0, 0), author_text, font=author_font)
    author_width = bbox[2] - bbox[0]
    draw.text(
        ((width - author_width) // 2, y_offset + 50),
        author_text,
        fill='#bdc3c7',
        font=author_font
    )
    
    # Draw badge
    badge_text = "Modernized Student Edition"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_width = bbox[2] - bbox[0]
    badge_y = height - 300
    
    # Badge background
    draw.rectangle(
        [(width//2 - badge_width//2 - 30, badge_y - 20),
         (width//2 + badge_width//2 + 30, badge_y + 50)],
        fill='#3498db'
    )
    
    draw.text(
        ((width - badge_width) // 2, badge_y),
        badge_text,
        fill='white',
        font=badge_font
    )
    
    # Save
    cover_path = paths["deliverables_ebook"] / f"{slug}_cover.png"
    img.save(cover_path, "PNG")
    
    logger.info(f"Template cover generated: {cover_path}")
    return cover_path


def generate_cover(
    metadata: PublishingMetadata,
    slug: str,
    use_ai: bool = True
) -> CoverDesign:
    """Generate book cover (AI or template).
    
    Args:
        metadata: Publishing metadata
        slug: Project slug
        use_ai: Whether to use DALL-E (True) or template (False)
        
    Returns:
        CoverDesign object with path to generated cover
    """
    if use_ai:
        cover_path = generate_cover_with_dalle(metadata, slug)
    else:
        cover_path = generate_cover_template(metadata, slug)
    
    return CoverDesign(
        image_path=str(cover_path),
        title=metadata.title,
        subtitle=metadata.subtitle,
        author=metadata.author,
        publisher=metadata.publisher
    )
