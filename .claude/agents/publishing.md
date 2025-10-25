# Publishing Pipeline Agent

**Command**: `/publishing`

## Purpose

Expert in publishing and distribution workflow for Lily Books, with focus on the transition from Draft2Digital/Amazon KDP/Google Play Books to **PublishDrive as the primary distributor**.

## Key Knowledge Areas

### 1. PublishDrive Integration ⭐ PRIMARY

**Status**: Primary distribution aggregator (manual upload)

**File**: [src/lily_books/tools/uploaders/publishdrive.py](../../src/lily_books/tools/uploaders/publishdrive.py)

**Why PublishDrive**:
- **Single upload** → **400+ stores** (Amazon KDP, Apple Books, Google Play, Kobo, B&N, Scribd, OverDrive, etc.)
- **Free ISBN** assignment via PublishDrive dashboard
- **Unified analytics** dashboard for all retailers
- **No exclusivity** requirements
- **Multi-currency** pricing
- **Better royalties** than individual uploads

**Current Implementation**: Stub (manual upload required)
- Generates detailed manual upload instructions ([publishdrive.py:102-200](../../src/lily_books/tools/uploaders/publishdrive.py#L102-L200))
- No API available from PublishDrive
- Selenium automation planned for future phase

**Upload Node**: [src/lily_books/graph.py:1400](../../src/lily_books/graph.py#L1400)
```python
# PRIMARY: PublishDrive
graph.add_node("upload_publishdrive", upload_to_publishdrive_node)
```

**Manual Upload Process**:
1. Create PublishDrive account
2. Add new book
3. Fill metadata (title, author, description, keywords, BISAC)
4. Upload EPUB manuscript
5. Upload cover image
6. Select distribution channels (400+ stores)
7. Set pricing
8. Submit for distribution
9. Get free ISBN assignment

---

### 2. Legacy/Backup Integrations (DEPRECATED)

These integrations are **deprecated** but kept as **functional backups**:

#### Draft2Digital (LEGACY - Fully Functional API)
**File**: [src/lily_books/tools/uploaders/draft2digital.py](../../src/lily_books/tools/uploaders/draft2digital.py)

**Status**: DEPRECATED (but fully functional)
- Complete API integration
- Free ISBN assignment
- Distribution to 400+ stores (same as PublishDrive)
- Kept as backup if PublishDrive unavailable

**Why Deprecated**:
- PublishDrive offers better royalties
- Single dashboard vs multiple
- More direct retailer relationships

#### Amazon KDP (LEGACY - Stub)
**File**: [src/lily_books/tools/uploaders/amazon_kdp.py](../../src/lily_books/tools/uploaders/amazon_kdp.py)

**Status**: DEPRECATED stub implementation
- Generates manual upload instructions
- Free ASIN assignment
- 70% royalty tier ($2.99-9.99)
- Kept as backup for Amazon-exclusive releases

#### Google Play Books (LEGACY - Stub)
**File**: [src/lily_books/tools/uploaders/google_play.py](../../src/lily_books/tools/uploaders/google_play.py)

**Status**: DEPRECATED stub implementation
- Generates manual upload instructions
- Free Google ID assignment
- 52% revenue share
- Kept as backup for Google-exclusive releases

---

### 3. Publishing Pipeline Flow ([src/lily_books/graph.py:1390-1513](../../src/lily_books/graph.py#L1390-L1513))

**Nodes** (only added if `ENABLE_PUBLISHING=true`):

1. **assign_identifiers** ([tools/identifiers.py](../../src/lily_books/tools/identifiers.py))
   - Assign ASIN (Amazon), ISBN (PublishDrive/D2D), Google ID

2. **prepare_editions** ([tools/edition_manager.py](../../src/lily_books/tools/edition_manager.py))
   - Create Kindle edition (KF8 format)
   - Create Universal edition (EPUB 3.0)

3. **generate_retail_metadata** ([chains/retail_metadata.py](../../src/lily_books/chains/retail_metadata.py))
   - AI-powered SEO metadata generation
   - BISAC category selection
   - Keyword optimization
   - Description variants

4. **calculate_pricing** ([tools/pricing.py](../../src/lily_books/tools/pricing.py))
   - Optimize for 70% Amazon royalty tier ($2.99-9.99)
   - Calculate delivery costs
   - Multi-currency conversion

5. **validate_metadata** ([tools/validators/metadata_validator.py](../../src/lily_books/tools/validators/metadata_validator.py))
   - Check retailer requirements
   - Validate BISAC codes
   - Verify required fields

6. **validate_epub** ([tools/validators/epub_validator.py](../../src/lily_books/tools/validators/epub_validator.py))
   - Run epubcheck validation
   - Check EPUB quality score
   - Verify TOC and navigation

7. **human_review** ([tools/human_review.py](../../src/lily_books/tools/human_review.py))
   - Manual approval gate
   - Optional (disable with `ENABLE_HUMAN_REVIEW=false`)

8. **upload_publishdrive** ([tools/uploaders/publishdrive.py](../../src/lily_books/tools/uploaders/publishdrive.py))
   - **PRIMARY** upload node
   - Generates manual instructions
   - Goes directly to publishing report

9. **upload_amazon** ([tools/uploaders/amazon_kdp.py](../../src/lily_books/tools/uploaders/amazon_kdp.py))
   - **LEGACY** backup
   - Stub implementation

10. **upload_google** ([tools/uploaders/google_play.py](../../src/lily_books/tools/uploaders/google_play.py))
    - **LEGACY** backup
    - Stub implementation

11. **upload_d2d** ([tools/uploaders/draft2digital.py](../../src/lily_books/tools/uploaders/draft2digital.py))
    - **LEGACY** backup
    - Full API implementation

12. **publishing_report** ([tools/publishing_dashboard.py](../../src/lily_books/tools/publishing_dashboard.py))
    - Final status report
    - Upload results per retailer
    - Identifier assignments
    - Next steps

---

### 4. Conditional Routing ([graph.py:1473-1510](../../src/lily_books/graph.py#L1473-L1510))

**After Human Review**:
```python
def route_after_review(state: FlowState) -> str:
    if not state.get("human_approved", False):
        return "end_without_upload"

    # PRIMARY: PublishDrive (if selected)
    if "publishdrive" in config.target_retailers:
        return "upload_publishdrive"

    # LEGACY: Individual retailers
    if "amazon" in config.target_retailers:
        return "upload_amazon"
    elif "google" in config.target_retailers:
        return "upload_google"
    elif "draft2digital" in config.target_retailers:
        return "upload_d2d"

    return "end_without_upload"
```

**PRIMARY Flow**: PublishDrive → Publishing Report (single upload)
**LEGACY Flow**: Amazon → Google → D2D → Publishing Report (sequential)

---

### 5. Configuration

**Enable Publishing**:
```bash
# .env
ENABLE_PUBLISHING=true
TARGET_RETAILERS=publishdrive  # PRIMARY ⭐
# TARGET_RETAILERS=amazon,google,draft2digital  # LEGACY backup
```

**API Keys** (for legacy integrations):
```bash
# Draft2Digital (LEGACY - functional backup)
DRAFT2DIGITAL_API_KEY=your-d2d-api-key

# Amazon KDP (no API - manual only)
# KDP_EMAIL=your-email
# KDP_PASSWORD=your-password

# Google Play Books (no API - manual only)
# GOOGLE_PLAY_CREDENTIALS_PATH=/path/to/credentials.json
```

**Pricing**:
```bash
DEFAULT_PRICE_USD=2.99  # Optimal for 70% Amazon royalty
```

**Human Review**:
```bash
ENABLE_HUMAN_REVIEW=true  # Require manual approval before upload
```

---

## Key Files

**PRIMARY (PublishDrive)**:
- [src/lily_books/tools/uploaders/publishdrive.py](../../src/lily_books/tools/uploaders/publishdrive.py) - Stub with manual instructions
- [src/lily_books/graph.py:1400](../../src/lily_books/graph.py#L1400) - Upload node

**LEGACY/BACKUP**:
- [src/lily_books/tools/uploaders/draft2digital.py](../../src/lily_books/tools/uploaders/draft2digital.py) - D2D API (functional)
- [src/lily_books/tools/uploaders/amazon_kdp.py](../../src/lily_books/tools/uploaders/amazon_kdp.py) - KDP stub
- [src/lily_books/tools/uploaders/google_play.py](../../src/lily_books/tools/uploaders/google_play.py) - Google stub

**Supporting Tools**:
- [src/lily_books/tools/identifiers.py](../../src/lily_books/tools/identifiers.py) - ID assignment
- [src/lily_books/tools/edition_manager.py](../../src/lily_books/tools/edition_manager.py) - Edition prep
- [src/lily_books/chains/retail_metadata.py](../../src/lily_books/chains/retail_metadata.py) - SEO metadata
- [src/lily_books/tools/pricing.py](../../src/lily_books/tools/pricing.py) - Pricing optimization
- [src/lily_books/tools/validators/metadata_validator.py](../../src/lily_books/tools/validators/metadata_validator.py) - Metadata validation
- [src/lily_books/tools/validators/epub_validator.py](../../src/lily_books/tools/validators/epub_validator.py) - EPUB validation
- [src/lily_books/tools/human_review.py](../../src/lily_books/tools/human_review.py) - Approval gate
- [src/lily_books/tools/publishing_dashboard.py](../../src/lily_books/tools/publishing_dashboard.py) - Status reporting

---

## Common Questions

### Q: Why transition from Draft2Digital to PublishDrive?

**Answer**:

**Benefits of PublishDrive**:
1. **Better royalties**: More favorable revenue share than D2D
2. **Direct relationships**: Closer to retailers than aggregator
3. **Unified dashboard**: Single analytics interface for all stores
4. **Free ISBN**: Same as D2D, but with PublishDrive branding
5. **Multi-currency**: Better international pricing
6. **No exclusivity**: Same as D2D (no lock-in)
7. **400+ stores**: Same distribution reach as D2D

**Why keep D2D as backup**:
- Fully functional API integration
- Proven reliability
- Fallback if PublishDrive unavailable
- Testing and comparison

**Migration path**:
- NEW books: Use PublishDrive
- EXISTING D2D books: Leave in place (no rush to migrate)
- FUTURE: Evaluate PublishDrive performance, potentially migrate D2D catalog

---

### Q: How do I upload to PublishDrive?

**Answer**:

**Current Process** (Manual Upload):

1. **Run pipeline with PublishDrive enabled**:
   ```bash
   ENABLE_PUBLISHING=true TARGET_RETAILERS=publishdrive \
   python -m lily_books run 1342 --slug pride-and-prejudice
   ```

2. **Get upload instructions**:
   - Pipeline generates detailed manual instructions
   - Includes all metadata, EPUB path, cover path
   - Step-by-step upload guide

3. **Follow instructions**:
   - Create PublishDrive account
   - Upload EPUB and cover
   - Fill metadata from generated instructions
   - Select distribution channels (400+ stores)
   - Submit for distribution

4. **Record ISBN**:
   - PublishDrive assigns free ISBN
   - Update `books/{slug}/meta/publish.json` with ISBN

**Future** (Selenium Automation):
- Planned for Phase 3
- Will automate entire upload process
- Extract ISBN automatically
- Return success with identifiers

---

### Q: How do I test publishing without actually uploading?

**Answer**:

**Testing Strategies**:

1. **Disable Human Review** (skip upload):
   ```bash
   ENABLE_PUBLISHING=true \
   ENABLE_HUMAN_REVIEW=false \  # Skips approval gate
   python -m lily_books run 11 --slug test-book
   ```

2. **Check validation gates**:
   - Pipeline runs validate_metadata and validate_epub
   - Errors caught before upload
   - Review `books/{slug}/meta/publish.json`

3. **Inspect generated metadata**:
   ```bash
   cat books/{slug}/meta/publish.json
   ```

4. **Review edition files**:
   ```bash
   ls books/{slug}/deliverables/ebook/
   # Should see: {slug}_kindle.epub, {slug}_universal.epub
   ```

5. **Check manual instructions**:
   - Upload result includes full instructions
   - Verify all metadata populated correctly

---

### Q: What's the difference between Kindle and Universal editions?

**Answer**:

**Kindle Edition** ([edition_manager.py](../../src/lily_books/tools/edition_manager.py)):
- **Target**: Amazon KDP only
- **Format**: KF8 (Kindle Format 8)
- **Features**: Amazon-specific enhancements
- **Identifier**: ASIN (auto-assigned by Amazon)

**Universal Edition**:
- **Target**: All other retailers (PublishDrive, Apple, Google, Kobo, B&N, etc.)
- **Format**: EPUB 3.0 (industry standard)
- **Features**: Broad compatibility
- **Identifier**: ISBN (free from PublishDrive/D2D)

**Why Two Editions**:
- Amazon prefers KF8 format
- Other retailers require EPUB 3.0
- Optimizes for each platform's requirements

**File Paths**:
```
books/{slug}/deliverables/ebook/
  {slug}_kindle.epub  # For Amazon only
  {slug}_universal.epub  # For PublishDrive (all other stores)
```

---

### Q: How does SEO metadata generation work?

**Answer**:

**AI-Powered Metadata** ([chains/retail_metadata.py](../../src/lily_books/chains/retail_metadata.py)):

Uses Claude 4.5 Haiku to generate:

1. **BISAC Categories** (up to 3):
   - Industry-standard classification
   - Examples: FIC004000 (Fiction/Classics), FIC027050 (Romance/Historical)

2. **SEO Keywords** (20 keywords):
   - Customer search terms
   - Optimized for discoverability
   - Examples: "modernized classics", "student-friendly", "Jane Austen"

3. **Short Description** (150 chars):
   - Elevator pitch for search results
   - Hooks customer interest

4. **Long Description** (800-1500 words):
   - Full product page description
   - HTML formatted
   - Selling points, benefits, target audience

5. **Competitive Titles**:
   - Similar/comparable books
   - Helps retailers recommend

**Generated From**:
- Book title and author
- Chapter content (first 3 chapters)
- Original Gutenberg description
- Target audience (students, grade 7-9)

**Optimization**:
- Keyword density
- Readability
- Conversion-focused copy

---

### Q: How does pricing optimization work?

**Answer**:

**Goal**: Maximize revenue while meeting Amazon's 70% royalty tier

**Amazon 70% Royalty Requirements** ([tools/pricing.py](../../src/lily_books/tools/pricing.py)):
- Price between $2.99 and $9.99
- Delivery cost < 10% of list price
- Higher royalty than 35% tier

**Default Pricing**:
- **$2.99** - Optimal price point
- **70% royalty**: $2.09 per sale
- **Low delivery cost**: ~$0.06 per EPUB

**Calculation**:
```python
list_price = $2.99
amazon_royalty_70 = list_price * 0.70 = $2.09
delivery_cost = epub_size_mb * $0.06/MB = ~$0.06
net_royalty = $2.09 - $0.06 = $2.03 per sale
```

**Comparison to 35% Tier**:
- 35% of $2.99 = $1.05
- 70% tier nets ~2x more per sale

**Other Retailers**:
- **Google Play**: 52% of list price = $1.55
- **Apple (via PublishDrive)**: ~63% of list price = $1.88
- **Kobo (via PublishDrive)**: ~60% of list price = $1.79

---

### Q: When will Selenium automation be implemented?

**Answer**:

**Current Status**:
- PublishDrive stub implementation (manual upload)
- Full instructions generated by pipeline
- Deferred to future phase

**Roadmap**:
- **Phase 1** (DONE): Free distribution infrastructure
- **Phase 2** (DONE): Draft2Digital API integration
- **Phase 3** (PLANNED): Selenium automation for PublishDrive
  - Headless Chrome/Firefox
  - Login + upload automation
  - Metadata form filling
  - ISBN extraction
  - Error handling
- **Phase 4** (OPTIONAL): Amazon KDP automation (if needed)

**Why Deferred**:
- PublishDrive manual upload is fast (15-20 min)
- Focus on core pipeline quality first
- Selenium adds complexity and fragility
- Manual process works for MVP

**When to Implement**:
- Publishing >10 books/month
- Manual upload becomes bottleneck
- ROI justifies maintenance cost

---

## Best Practices

### 1. Always Use PublishDrive (PRIMARY)
- Single upload → 400+ stores
- Better royalties than individual uploads
- Free ISBN

### 2. Keep Legacy Integrations as Backups
- D2D API is fully functional
- Use if PublishDrive unavailable
- Testing and comparison

### 3. Validate Before Upload
- Run epubcheck validation
- Check metadata completeness
- Review generated instructions

### 4. Test with Single Chapter
- `--chapters 1` for fast testing
- Verify metadata generation
- Check edition creation

### 5. Record ISBNs
- Update `publish.json` with assigned ISBN
- Track distribution status
- Monitor sales per retailer

---

## Related Agents

- [/langgraph-pipeline](langgraph-pipeline.md) - For publishing node flow
- [/epub-covers](epub-covers.md) - For EPUB and cover generation
- [/testing](testing.md) - For testing publishing without uploads

---

**Last Updated**: 2025-10-25
**Version**: 1.0
