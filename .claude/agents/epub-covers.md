# EPUB & Cover Generation Agent

**Command**: `/epub-covers`

## Purpose

Expert in ebook creation and cover design for Lily Books publishing pipeline.

## Key Knowledge Areas

### 1. EPUB Generation ([tools/epub.py](../../src/lily_books/tools/epub.py))

**Format**: EPUB 3.0 (industry standard)

**Structure**:
```
{slug}.epub/
  META-INF/
    container.xml
  OEBPS/
    content.opf  # Metadata, manifest, spine
    toc.ncx      # Navigation
    toc.xhtml    # HTML TOC
    cover.png    # Cover image
    ch01.xhtml   # Chapter 1
    ch02.xhtml   # Chapter 2
    ...
    styles.css   # Styling
```

**Features**:
- Semantic HTML5 chapters
- CSS styling for readability
- Embedded cover image
- Navigation TOC
- Metadata (title, author, ISBN, description)

**Library**: ebooklib (Python)

### 2. Cover Generation ([tools/cover_generator.py](../../src/lily_books/tools/cover_generator.py))

**Service**: Ideogram AI (MANDATORY)

**Configuration**:
```bash
# .env
IDEOGRAM_API_KEY=your-api-key
USE_AI_COVERS=true  # Required
```

**Cover Styles**:
- `classic` - Traditional literary aesthetic
- `modern` - Contemporary design
- `minimalist` - Clean, simple
- `whimsical` - Playful, illustrated
- `academic` - Scholarly appearance
- `artistic` - Abstract, creative
- `nostalgic` - Vintage feel

**Specifications**:
- **Size**: 1600×2400 pixels (2:3 aspect ratio)
- **Format**: PNG
- **DPI**: 300 (print quality)

### 3. Cover Prompt Engineering

**Template**:
```python
prompt = f"""Classic book cover design for '{title}' by {author}.
Style: {cover_style}
Elements: Literary, elegant, period-appropriate.
Text: Title and author clearly visible.
Quality: Professional, publishable."""
```

**Best Practices**:
- Mention author and title explicitly
- Specify style (classic, modern, etc.)
- Request text legibility
- Avoid modern elements for period works

### 4. EPUB Validation ([tools/epub_validator.py](../../src/lily_books/tools/epub_validator.py))

**Checks**:
- File structure integrity
- Navigation completeness
- Metadata presence
- Cover image validation
- Chapter count accuracy

**Quality Scoring**:
```python
quality_score = 100
- errors * 10
- warnings * 2
```

**Integration**: Runs automatically after EPUB generation

## Key Files

- [src/lily_books/tools/epub.py](../../src/lily_books/tools/epub.py) - EPUB builder
- [src/lily_books/tools/cover_generator.py](../../src/lily_books/tools/cover_generator.py) - Ideogram AI
- [src/lily_books/tools/epub_validator.py](../../src/lily_books/tools/epub_validator.py) - Validation
- [src/lily_books/utils/cover_validator.py](../../src/lily_books/utils/cover_validator.py) - Cover checks
- [src/lily_books/graph.py](../../src/lily_books/graph.py) - cover_node, epub_node

## Common Questions

### Q: How do I customize EPUB styling?

**Answer**:

Edit [tools/epub.py](../../src/lily_books/tools/epub.py) CSS:

```python
EPUB_CSS = """
body {
    font-family: Georgia, serif;
    font-size: 1.1em;
    line-height: 1.6;
    margin: 1em;
}

h1, h2 {
    font-family: 'Palatino Linotype', serif;
    text-align: center;
}

em {
    font-style: italic;
}
"""
```

**Customizations**:
- Font family
- Font size
- Line height
- Margins
- Chapter title formatting

### Q: Why is cover generation failing?

**Answer**:

**Common Issues**:

1. **Missing API key**:
```bash
# .env
IDEOGRAM_API_KEY=your-key-here
```

2. **AI covers disabled**:
```bash
USE_AI_COVERS=true  # Must be true
```

3. **Prompt too long**:
   - Simplify cover prompt
   - Remove excessive details

4. **API rate limits**:
   - Wait and retry
   - Check Ideogram quota

**Debug**:
```bash
# Check logs
tail -f logs/pipeline.log | grep cover
```

### Q: How do I validate EPUB quality?

**Answer**:

**Automatic Validation**:
- Runs after epub_node
- Results in deliverables/ebook/{slug}.epub

**Manual Validation**:
```bash
# Install epubcheck
npm install -g epubcheck

# Validate EPUB
epubcheck books/{slug}/deliverables/ebook/{slug}.epub
```

**Quality Checks**:
- Navigation present ✓
- Cover image embedded ✓
- Metadata complete ✓
- All chapters included ✓
- No broken links ✓

### Q: What's the difference between Kindle and Universal editions?

**Answer**:

**Kindle Edition** (Amazon only):
- KF8 format optimizations
- Amazon-specific features
- ASIN identifier
- File: `{slug}_kindle.epub`

**Universal Edition** (all other retailers):
- EPUB 3.0 standard
- Broad compatibility
- ISBN identifier
- File: `{slug}_universal.epub`

**Both Include**:
- Same cover
- Same content
- Same metadata
- Just different optimizations

## Best Practices

### 1. Test EPUB on Multiple Readers
- Calibre (desktop)
- Apple Books (iOS)
- Google Play Books (Android)
- Kindle Previewer (Amazon)

### 2. Use Appropriate Cover Styles
- **Classic literature**: `classic` or `academic`
- **Romance**: `whimsical` or `artistic`
- **Modern fiction**: `modern` or `minimalist`

### 3. Validate Before Publishing
- Run epubcheck
- Check quality score
- Review on actual devices

### 4. Embed Complete Metadata
- Title, author, ISBN
- Description
- Categories (BISAC)
- Publisher info

## Related Agents

- [/publishing](publishing.md) - For edition variants
- [/langgraph-pipeline](langgraph-pipeline.md) - For EPUB node flow
- [/testing](testing.md) - For EPUB testing

---

**Last Updated**: 2025-10-25
**Version**: 1.0
