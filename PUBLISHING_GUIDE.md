# Publishing & Distribution Guide

## Overview

This guide documents the **free distribution system** integrated into the lily-books pipeline. The system enables automated preparation and distribution of modernized classics to major ebook retailers using **100% free channels**:

- **Amazon KDP** (Free ASIN)
- **Google Play Books** (Free Google ID)
- **Apple Books via Draft2Digital** (Free ISBN + distribution to 400+ stores)

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Configuration](#configuration)
4. [Pipeline Nodes](#pipeline-nodes)
5. [Retailer Setup](#retailer-setup)
6. [Running the Pipeline](#running-the-pipeline)
7. [Edition Strategy](#edition-strategy)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Enable Publishing in Configuration

Add to your `.env` file:

```bash
# Enable publishing pipeline
ENABLE_PUBLISHING=true

# Target retailers (comma-separated)
TARGET_RETAILERS=amazon,google,draft2digital

# Default pricing
DEFAULT_PRICE_USD=2.99

# Human review (set to false to auto-approve)
ENABLE_HUMAN_REVIEW=true

# Retailer API credentials (optional for initial setup)
# KDP_EMAIL=your-kdp-email@example.com
# KDP_PASSWORD=your-kdp-password
# GOOGLE_PLAY_CREDENTIALS_PATH=/path/to/google-service-account.json
# DRAFT2DIGITAL_API_KEY=your-d2d-api-key
```

### 2. Install Dependencies

```bash
# Core dependencies (already in pyproject.toml)
poetry install

# Optional: Install epubcheck for EPUB validation
# macOS
brew install epubcheck

# Ubuntu/Debian
sudo apt-get install epubcheck

# Or download from: https://github.com/w3c/epubcheck/releases
```

### 3. Run the Pipeline

```bash
# Run full pipeline including publishing
poetry run python -m lily_books run 1342 --slug pride-and-prejudice

# The pipeline will:
# 1. Modernize the text
# 2. Generate EPUB
# 3. Generate cover
# 4. Assign free identifiers
# 5. Prepare editions (Kindle + Universal)
# 6. Generate SEO metadata
# 7. Calculate optimal pricing
# 8. Validate EPUB and metadata
# 9. Present for human review
# 10. Display upload instructions
```

---

## Architecture Overview

### Pipeline Flow

The publishing pipeline extends the existing modernization pipeline:

```
EXISTING PIPELINE:
ingest → chapterize → rewrite → qa_text → metadata → cover → epub

NEW PUBLISHING PIPELINE (when ENABLE_PUBLISHING=true):
epub → assign_identifiers → prepare_editions → generate_retail_metadata →
calculate_pricing → validate_metadata → validate_epub → human_review →
upload_amazon → upload_google → upload_d2d → publishing_report → END
```

### Key Components

| Component | Purpose | File |
|-----------|---------|------|
| **Identifier Manager** | Assigns free ASIN, Google ID, D2D ISBN | `tools/identifiers.py` |
| **Edition Manager** | Prepares Kindle + Universal editions | `tools/edition_manager.py` |
| **Metadata Generator** | Creates SEO-optimized metadata | `chains/retail_metadata.py` |
| **Pricing Optimizer** | Calculates optimal pricing | `tools/pricing.py` |
| **EPUB Validator** | Validates with epubcheck | `tools/validators/epub_validator.py` |
| **Metadata Validator** | Checks retailer requirements | `tools/validators/metadata_validator.py` |
| **Human Review Gate** | Manual approval checkpoint | `tools/human_review.py` |
| **Uploaders** | Retailer-specific upload logic | `tools/uploaders/` |
| **Dashboard** | Status tracking and reporting | `tools/publishing_dashboard.py` |

---

## Configuration

### Environment Variables

```bash
# ===== PUBLISHING SETTINGS =====

# Enable publishing pipeline (default: false)
ENABLE_PUBLISHING=true

# Target retailers (comma-separated list)
# Options: amazon, google, draft2digital
TARGET_RETAILERS=amazon,google,draft2digital

# Default ebook price in USD
DEFAULT_PRICE_USD=2.99

# Require human approval before uploading (default: true)
ENABLE_HUMAN_REVIEW=true

# Path to epubcheck executable (default: "epubcheck")
EPUBCHECK_PATH=epubcheck


# ===== RETAILER API CREDENTIALS =====

# Amazon KDP (for Selenium automation - optional)
# Note: Currently stub implementation, manual upload required
KDP_EMAIL=your-kdp-email@example.com
KDP_PASSWORD=your-kdp-password

# Google Play Books API (optional)
# Set path to Google Cloud service account JSON file
GOOGLE_PLAY_CREDENTIALS_PATH=/path/to/service-account.json

# Draft2Digital API (optional)
# Get API key from: https://draft2digital.com/settings/api
DRAFT2DIGITAL_API_KEY=your-d2d-api-key
```

### Configuration in Code

```python
from lily_books.config import settings

# Check if publishing is enabled
if settings.enable_publishing:
    print(f"Publishing to: {settings.target_retailers}")
    print(f"Default price: ${settings.default_price_usd}")
```

---

## Pipeline Nodes

### 1. Assign Identifiers (`assign_identifiers_node`)

**Purpose:** Assigns free identifiers for each distribution channel.

**Process:**
- Determines edition strategy based on target retailers
- Creates **Kindle Edition** (ASIN) for Amazon
- Creates **Universal Edition** (ISBN or Google ID) for other retailers
- Generates edition-specific metadata

**Output:**
```python
state["identifiers"] = {
    "editions": [
        {
            "name": "Kindle Edition",
            "retailer": "amazon_kdp",
            "identifier": {
                "identifier_type": "ASIN",
                "identifier_value": None,  # Assigned at upload
                "source": "amazon_auto_assign",
                "cost": 0.0,
                "exclusive": True
            },
            "file_suffix": "_kindle",
            "exclusive_to": "amazon"
        },
        {
            "name": "Universal Edition",
            "retailer": "draft2digital",
            "identifier": {
                "identifier_type": "ISBN",
                "identifier_value": None,  # Assigned at upload
                "source": "draft2digital_free_isbn",
                "cost": 0.0,
                "exclusive": False
            },
            "file_suffix": "_universal",
            "distribution_to": ["apple", "kobo", "bn", "scribd", "overdrive"]
        }
    ]
}
```

### 2. Prepare Editions (`prepare_editions_node`)

**Purpose:** Creates edition-specific EPUB files.

**Process:**
- Copies base EPUB to `editions/` directory
- Creates `{slug}_kindle.epub` for Amazon
- Creates `{slug}_universal.epub` for D2D/Google

**Output:**
```python
state["edition_files"] = [
    {
        "edition_name": "Kindle Edition",
        "retailer": "amazon_kdp",
        "file_path": "books/pride-and-prejudice/deliverables/ebook/editions/pride-and-prejudice_kindle.epub",
        "identifier_type": "ASIN"
    },
    {
        "edition_name": "Universal Edition",
        "retailer": "draft2digital",
        "file_path": "books/pride-and-prejudice/deliverables/ebook/editions/pride-and-prejudice_universal.epub",
        "identifier_type": "ISBN"
    }
]
```

### 3. Generate Retail Metadata (`generate_retail_metadata_node`)

**Purpose:** Creates SEO-optimized metadata using AI.

**Process:**
- Uses GPT-4o-mini to generate:
  - 3 title variations for A/B testing
  - Compelling subtitle
  - 150-char short description
  - 800-1500 word long description (HTML formatted)
  - 20 SEO keywords
  - 7 Amazon-specific keywords
  - BISAC category codes
  - Competitive titles

**Example Output:**
```python
state["retail_metadata"] = {
    "title_variations": [
        "Pride and Prejudice",
        "Pride and Prejudice: A Modern English Edition",
        "Pride and Prejudice (Accessible Classic)"
    ],
    "subtitle": "A Modernized Edition for Contemporary Readers",
    "description_short": "Experience Jane Austen's timeless romance in clear, modern English...",
    "description_long": "<h2>About This Edition</h2><p>This modernized edition...</p>",
    "keywords": [
        "pride and prejudice modern english",
        "pride and prejudice easy to read",
        "jane austen accessible",
        "modernized classics",
        ...
    ],
    "amazon_keywords": [
        "pride prejudice modern",
        "accessible classics",
        "student edition",
        ...
    ],
    "bisac_categories": [
        "FIC004000",  # Fiction / Classics
        "EDU029010",  # Education / Teaching Methods
        "FIC019000"   # Fiction / Literary
    ]
}
```

### 4. Calculate Pricing (`calculate_pricing_node`)

**Purpose:** Determines optimal pricing across retailers.

**Strategy:**
- Base price on estimated page count
- Ensure ≥ $2.99 for Amazon 70% royalty tier
- Apply configured default if set

**Output:**
```python
state["pricing"] = {
    "base_price_usd": 2.99,
    "amazon": {
        "usd": 2.99,
        "royalty_tier": "70%",
        "royalty_amount": 2.09  # $2.99 * 0.70
    },
    "google": {
        "usd": 2.99,
        "royalty_amount": 1.55,  # $2.99 * 0.52
        "note": "Google converts to local currency"
    },
    "apple_via_d2d": {
        "usd": 2.99,
        "royalty_amount": 1.79,  # $2.99 * 0.60
        "note": "D2D handles currency conversion"
    },
    "reasoning": "Optimized for Amazon 70% royalty tier"
}
```

### 5. Validate Metadata (`validate_metadata_node`)

**Purpose:** Ensures metadata meets retailer requirements.

**Checks:**
- **Amazon:** Title ≤200 chars, subtitle ≤200, description ≤4000, ≤7 keywords, ≤2 categories
- **Google:** Title ≤255 chars, description ≥200 and ≤4000
- **Apple:** Title ≤255 chars, description ≤4000

### 6. Validate EPUB (`validate_epub_node`)

**Purpose:** Validates EPUB files using epubcheck.

**Process:**
- Runs `epubcheck` on each edition EPUB
- Parses JSON output for errors/warnings
- Creates validation report

**Note:** If `epubcheck` is not installed, validation is skipped with a warning.

### 7. Human Review Gate (`human_review_node`)

**Purpose:** Manual approval checkpoint before uploading.

**Displays:**
- Title, author, price
- Target retailers and editions
- Validation status
- Cover path
- EPUB file paths
- Metadata preview

**Interactive Prompt:**
```
======================================================================
                        HUMAN REVIEW REQUIRED
======================================================================

Title: Pride and Prejudice
Author: Jane Austen
Price: $2.99 USD

Target Retailers: amazon, google, draft2digital

Editions:
  - Kindle Edition: ASIN via amazon_kdp
  - Universal Edition: ISBN via draft2digital
    Distribution: apple, kobo, bn, scribd, overdrive

Validation Status:
  Metadata: ✓ PASS
  EPUB: ✓ PASS

----------------------------------------------------------------------
Approve for publishing? (yes/no):
```

**Bypass:** Set `ENABLE_HUMAN_REVIEW=false` to auto-approve.

### 8. Retailer Uploads

**Current Implementation:** STUB (documentation only)

The upload nodes currently provide **detailed setup instructions** for each retailer:

#### Amazon KDP (`upload_to_kdp_node`)
- Displays manual upload steps
- Documents form fields and requirements
- Explains ASIN assignment process

#### Google Play Books (`upload_to_google_node`)
- Shows API setup instructions
- Documents OAuth 2.0 authentication
- Provides Python code examples

#### Draft2Digital (`upload_to_d2d_node`)
- Shows API setup instructions
- Documents API endpoints
- Provides Python code examples

**Future Implementation:** Replace stubs with actual API/automation code.

### 9. Publishing Report (`generate_publishing_report_node`)

**Purpose:** Generates final status report and dashboard entry.

**Creates:**
- `dashboard/status.json` - Aggregate status across all books
- `dashboard/publishing_log.jsonl` - Detailed event log

**Example Report:**
```
======================================================================
                         PUBLISHING COMPLETE
======================================================================

PUBLISHING DASHBOARD
======================================================================

Title: Pride and Prejudice
Author: Jane Austen
Slug: pride-and-prejudice
Last Updated: 2025-10-24T10:30:00

Upload Status:
  ⏳ AMAZON: pending
  ⏳ GOOGLE: pending
  ⏳ DRAFT2DIGITAL: pending

Identifiers:
  - Kindle Edition: ASIN
  - Universal Edition: ISBN

Pricing: $2.99 USD

----------------------------------------------------------------------
```

---

## Retailer Setup

### Amazon KDP (Kindle Direct Publishing)

**Current Status:** STUB - Manual upload required

**Setup Steps:**

1. **Create KDP Account:**
   - Go to [https://kdp.amazon.com](https://kdp.amazon.com)
   - Sign up with Amazon account
   - Complete tax interview (W-9 for US, W-8 for international)
   - Add bank account for payments

2. **Manual Upload Process:**
   - Click "Create" → "Kindle eBook"
   - Fill metadata form:
     - Language: English
     - Title, subtitle, author
     - Description (from `retail_metadata.description_long`)
     - Keywords (from `retail_metadata.amazon_keywords`, max 7)
     - Categories (select 2 from BISAC codes)
     - Public domain: Yes
   - Upload manuscript (EPUB from `edition_files`)
   - Upload cover
   - Set pricing (ensure ≥ $2.99 for 70% royalty)
   - Select territories (Worldwide)
   - Publish

3. **Timeline:**
   - Review: 24-72 hours
   - ASIN assigned after approval
   - Book goes live after approval

**Future Enhancement:** Selenium automation (see implementation plan).

---

### Google Play Books Partner Program

**Current Status:** STUB - API setup required

**Setup Steps:**

1. **Join Partner Program:**
   - Apply at [https://play.google.com/books/publish](https://play.google.com/books/publish)
   - Approval: 2-5 business days

2. **Create Google Cloud Service Account:**
   ```bash
   # 1. Go to Google Cloud Console
   # 2. Create new project
   # 3. Enable "Google Books API"
   # 4. Create service account
   # 5. Download JSON key file
   # 6. Set GOOGLE_PLAY_CREDENTIALS_PATH
   ```

3. **Install Dependencies:**
   ```bash
   pip install google-api-python-client
   ```

4. **API Implementation:**
   ```python
   from google.oauth2 import service_account
   from googleapiclient.discovery import build

   credentials = service_account.Credentials.from_service_account_file(
       'service-account.json',
       scopes=['https://www.googleapis.com/auth/books']
   )
   service = build('books', 'v1', credentials=credentials)

   # Upload EPUB
   from googleapiclient.http import MediaFileUpload
   media = MediaFileUpload('book.epub', mimetype='application/epub+zip')
   volume = service.volumes().insert(body=metadata, media_body=media).execute()
   ```

5. **Timeline:**
   - Upload: Immediate
   - Processing: 1-2 days
   - Live: 3-5 days

**Docs:** [https://developers.google.com/books](https://developers.google.com/books)

---

### Draft2Digital (Apple Books + Wide Distribution)

**Current Status:** STUB - API setup required

**What You Get:**
- Free ISBN from D2D's pool
- Distribution to 400+ stores:
  - **Primary:** Apple Books, Kobo, Barnes & Noble
  - **Secondary:** Scribd, OverDrive (libraries), 24symbols, Tolino
- Universal Book Link (books2read.com)

**Setup Steps:**

1. **Create Account:**
   - Sign up at [https://draft2digital.com](https://draft2digital.com)
   - Free, instant access
   - No approval required

2. **Generate API Key:**
   - Go to Settings → API Access
   - Generate new API key
   - Set `DRAFT2DIGITAL_API_KEY` in `.env`

3. **API Implementation:**
   ```python
   import requests

   headers = {
       "Authorization": "Bearer YOUR_API_KEY",
       "Content-Type": "application/json"
   }

   # Create book
   book_data = {
       "title": "Pride and Prejudice",
       "authors": ["Jane Austen"],
       "description": "...",
       "price": {"amount": 2.99, "currency": "USD"},
       "distribution": {
           "apple": True,
           "kobo": True,
           "barnes_noble": True,
           "scribd": True
       }
   }

   response = requests.post(
       "https://www.draft2digital.com/api/v1/books",
       headers=headers,
       json=book_data
   )

   book_id = response.json()["book"]["id"]
   free_isbn = response.json()["book"]["isbn"]

   # Upload EPUB
   with open("book.epub", "rb") as f:
       files = {"file": f}
       requests.post(
           f"https://www.draft2digital.com/api/v1/books/{book_id}/manuscript",
           headers={"Authorization": "Bearer YOUR_API_KEY"},
           files=files
       )
   ```

4. **Timeline:**
   - Upload to D2D: Instant
   - Apple Books: 7-14 days
   - Kobo: 1-3 days
   - Barnes & Noble: 5-10 days

**Docs:** [https://draft2digital.com/api](https://draft2digital.com/api)

**Advantage:** Easiest API, free ISBN, widest distribution.

---

## Running the Pipeline

### Full Pipeline with Publishing

```bash
# Enable publishing in .env
ENABLE_PUBLISHING=true
TARGET_RETAILERS=amazon,google,draft2digital
DEFAULT_PRICE_USD=2.99
ENABLE_HUMAN_REVIEW=true

# Run pipeline
poetry run python -m lily_books run 1342 --slug pride-and-prejudice
```

### Publishing Only (Skip Modernization)

If you already have an EPUB and want to run publishing steps only:

```python
# This feature would require extending the CLI
# Future enhancement: poetry run python -m lily_books publish --slug pride-and-prejudice
```

### Batch Processing

Process multiple books:

```bash
# Future enhancement: Batch processing
# poetry run python -m lily_books batch --file books.csv
```

---

## Edition Strategy

### Why Two Editions?

**Problem:** Amazon ASIN locks the file to Amazon exclusively.

**Solution:** Create two separate editions:

1. **Kindle Edition** (Amazon-exclusive)
   - Uses free ASIN from Amazon
   - Optimized for Kindle readers
   - Cannot be distributed elsewhere

2. **Universal Edition** (Wide distribution)
   - Uses free ISBN from Draft2Digital
   - Distributed to Apple, Google, Kobo, etc.
   - Not on Amazon

### Edition Differentiation

Editions are **identical in content**, differentiated by:
- **Filename:** `{slug}_kindle.epub` vs `{slug}_universal.epub`
- **Retailer targeting:** Amazon vs. everyone else
- **Identifier:** ASIN vs. ISBN

**Future Enhancement:** Embed edition-specific metadata in EPUB.

### Legal & Contractual Considerations

✅ **Allowed:**
- Same book with different identifiers on different platforms
- Common practice in indie publishing
- Public domain content can be freely distributed

❌ **Not Allowed:**
- Using D2D ISBN on Amazon (they prefer ASINs)
- Enrolling in KDP Select while distributing elsewhere (would make Kindle edition exclusive)

**Recommendation:** Don't use KDP Select for wide distribution strategy.

---

## Troubleshooting

### EPUB Validation Fails

**Problem:** `epubcheck` reports errors.

**Solutions:**
1. Check if `epubcheck` is installed: `which epubcheck`
2. Install: `brew install epubcheck` (macOS) or download from [w3c/epubcheck](https://github.com/w3c/epubcheck/releases)
3. If not installed, validation is skipped with warning (safe to proceed)
4. Check EPUB manually: `epubcheck path/to/book.epub`

### Metadata Validation Fails

**Problem:** Metadata exceeds retailer limits.

**Solutions:**
1. Check error message for specific field (title, description, keywords)
2. Edit `retail_metadata` manually before upload
3. Adjust AI prompt in `chains/retail_metadata.py` to generate shorter content

### Human Review Blocks Pipeline

**Problem:** Need to review many books, slowing down batch processing.

**Solution:** Disable human review for trusted content:
```bash
ENABLE_HUMAN_REVIEW=false
```

**Warning:** Only disable for books you've manually reviewed offline.

### Upload Instructions Not Clear

**Problem:** Upload steps are complex.

**Solutions:**
1. Follow step-by-step instructions printed by each uploader
2. Check retailer documentation links provided
3. For Draft2Digital: Use web UI instead of API (easier for first upload)

### Missing Retailer Credentials

**Problem:** API keys not configured.

**Solution:**
- Credentials are **optional** for initial setup
- Uploaders will display setup instructions
- Follow instructions to create accounts and generate credentials
- Update `.env` file with credentials

### Graph Build Errors

**Problem:** `build_graph()` fails with missing imports.

**Solutions:**
1. Ensure all dependencies installed: `poetry install`
2. Check Python version: `python --version` (requires 3.10+)
3. Verify all new files exist in `tools/` and `chains/`

---

## Next Steps

### Phase 1: Initial Rollout (Current)
✅ Identifier management
✅ Edition preparation
✅ Metadata optimization
✅ Validation gates
✅ Human review
✅ Upload instructions (stubs)

### Phase 2: Retailer Integration (Next)
⬜ Draft2Digital API implementation
⬜ Google Play Books API implementation
⬜ Amazon KDP Selenium automation (or manual process docs)
⬜ Upload status monitoring

### Phase 3: Advanced Features (Future)
⬜ Batch processing multiple books
⬜ A/B testing for metadata
⬜ Sales analytics integration
⬜ Automated pricing optimization based on sales data
⬜ Category performance tracking

---

## FAQ

### Q: Do I need to pay for ISBNs?

**A:** No! This system uses 100% free identifiers:
- Amazon assigns free ASINs
- Google assigns free IDs
- Draft2Digital provides free ISBNs

### Q: Can I use my own ISBN?

**A:** Yes, but not necessary. To use your own:
1. Purchase ISBN from Bowker (US) or your country's agency
2. Modify `tools/identifiers.py` to use your ISBN
3. Update metadata in EPUB

### Q: Why not use KDP Select for Kindle Unlimited?

**A:** KDP Select requires **90-day exclusivity** (ebook can't be on other platforms). This conflicts with wide distribution strategy.

**Decision:** Prioritize wide distribution over KU revenue for maximum reach.

### Q: How long until books are live?

**Timeline:**
- Amazon KDP: 24-72 hours
- Google Play: 3-5 days
- Apple Books (via D2D): 7-14 days

### Q: Can I update books after publishing?

**A:** Yes! All platforms support updates:
- Upload new EPUB file
- Metadata changes take effect within 24 hours
- Price changes are immediate

### Q: What if I don't have retailer API credentials?

**A:** No problem! The pipeline will:
1. Generate all metadata and files
2. Validate everything
3. Display detailed manual upload instructions
4. You can upload via retailer web UIs

---

## Support

For issues, questions, or contributions:

1. **GitHub Issues:** [https://github.com/nydamon/lily-books/issues](https://github.com/nydamon/lily-books/issues)
2. **Documentation:** Check `MEMORY_BANK/` directory for technical specs
3. **Code:** Review `src/lily_books/tools/` for implementation details

---

**Happy Publishing! 📚✨**
