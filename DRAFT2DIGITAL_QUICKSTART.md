# Draft2Digital Integration - Quick Start Guide

## Overview

This guide shows you how to use the **fully functional Draft2Digital API integration** to automatically distribute your modernized classics to 400+ ebook retailers including Apple Books, Kobo, Barnes & Noble, Scribd, and OverDrive.

**Status:** ✅ **FULLY IMPLEMENTED** (Phase 2 Complete)

---

## Prerequisites

1. **Draft2Digital Account** (free)
   - Sign up at [https://draft2digital.com](https://draft2digital.com)
   - No approval required, instant access

2. **API Key**
   - Go to Settings → API Access
   - Generate new API key
   - Copy and save securely

3. **Environment Setup**
   - Add API key to `.env` file

---

## Setup (5 Minutes)

### Step 1: Create Draft2Digital Account

```bash
# Go to https://draft2digital.com/signup
# Fill in:
# - Email
# - Password
# - Author/Publisher name
# - Tax information (W-9 or W-8)
# - Payment info (bank account or PayPal)

# Instant approval - no waiting!
```

### Step 2: Generate API Key

```bash
# 1. Log in to Draft2Digital
# 2. Go to Settings → API Access
# 3. Click "Generate New API Key"
# 4. Copy the API key (starts with "d2d_")
```

### Step 3: Configure Environment

Add to your `.env` file:

```bash
# Enable publishing
ENABLE_PUBLISHING=true

# Target Draft2Digital for wide distribution
TARGET_RETAILERS=draft2digital

# Or include all retailers:
# TARGET_RETAILERS=amazon,google,draft2digital

# Draft2Digital API key
DRAFT2DIGITAL_API_KEY=d2d_your_api_key_here

# Pricing (optional, defaults to $2.99)
DEFAULT_PRICE_USD=2.99

# Auto-approve for automated workflows (optional)
ENABLE_HUMAN_REVIEW=false
```

---

## Usage

### Run Full Pipeline with D2D Upload

```bash
# Process and upload a book
poetry run python -m lily_books run 1342 --slug pride-and-prejudice

# Pipeline will:
# 1. Modernize text
# 2. Generate EPUB
# 3. Generate cover
# 4. Assign free identifiers (including D2D ISBN)
# 5. Prepare editions
# 6. Generate SEO metadata
# 7. Validate EPUB and metadata
# 8. Upload to Draft2Digital automatically
# 9. Receive free ISBN
# 10. Get universal book link (books2read.com)
```

### What Happens During Upload

The D2D integration performs these steps automatically:

1. **Create Book Entry**
   ```
   → Sends title, author, description, keywords, price to D2D
   → D2D assigns free ISBN-13
   → Returns book ID and ISBN
   ```

2. **Upload EPUB**
   ```
   → Uploads universal edition EPUB
   → D2D validates EPUB
   → Converts for different retailers
   ```

3. **Upload Cover**
   ```
   → Uploads cover image (JPEG or PNG)
   → D2D validates dimensions (min 1600x2400)
   ```

4. **Publish to Retailers**
   ```
   → Sends book to selected retailers:
     ✓ Apple Books
     ✓ Kobo
     ✓ Barnes & Noble
     ✓ Scribd
     ✓ OverDrive (libraries)
     ✓ Tolino (EU)
     ✓ Vivlio
     ✓ Palace Marketplace
     ✓ Bibliotheca
   → Creates universal book link (books2read.com)
   ```

### Expected Output

```
======================================================================
           📤 Draft2Digital Upload (API)
======================================================================

  📚 Uploading: Pride and Prejudice
  💰 Price: $2.99

  1️⃣ Creating book entry...
  ✓ Book created (ID: 12345, ISBN: 978-1-234567-89-0)

  2️⃣ Uploading EPUB...
  ✓ EPUB uploaded: pride-and-prejudice_universal.epub

  3️⃣ Uploading cover...
  ✓ Cover uploaded: pride-and-prejudice-cover.jpg

  4️⃣ Publishing to retailers...
  ✓ Published to retailers

  ✅ Upload complete!
  📖 Book ID: 12345
  🔖 Free ISBN: 978-1-234567-89-0
  🔗 Universal link: https://books2read.com/u/12345

✅ Draft2Digital upload successful!
📦 Distribution to: Apple Books, Kobo, B&N, Scribd, OverDrive, etc.
⏱️  Timeline: Apple Books (7-14 days), Kobo (1-3 days)

======================================================================
```

---

## Distribution Timeline

| Retailer | Timeline | Notes |
|----------|----------|-------|
| **Draft2Digital** | Instant | Book appears in your D2D dashboard immediately |
| **Kobo** | 1-3 days | Fastest distribution |
| **Barnes & Noble** | 5-10 days | Moderate speed |
| **Apple Books** | 7-14 days | Slowest but highest visibility |
| **Scribd** | 3-7 days | Subscription service |
| **OverDrive** | 7-14 days | Library distribution |
| **Others** | Varies | Tolino, Vivlio, Palace, etc. |

**Universal Book Link:** Available immediately at `books2read.com`

---

## Monitoring Your Books

### Via Draft2Digital Dashboard

```bash
# Go to https://draft2digital.com/books

# You'll see:
# - Book title, author, ISBN
# - Distribution status per retailer
# - Sales data (updated daily)
# - Pricing per territory
# - Cover preview
```

### Via Publishing Dashboard (Local)

```bash
# Check dashboard/status.json
cat dashboard/status.json | jq '.books[] | select(.title == "Pride and Prejudice")'

# Output shows:
# - Upload status
# - ISBN assigned
# - Universal book link
# - Timestamp
```

---

## Troubleshooting

### Issue: "API key not configured"

**Solution:**
```bash
# Check .env file has correct key
grep DRAFT2DIGITAL_API_KEY .env

# Should show:
# DRAFT2DIGITAL_API_KEY=d2d_your_key_here

# Verify key is valid by testing manually:
curl -H "Authorization: Bearer $DRAFT2DIGITAL_API_KEY" \
  https://www.draft2digital.com/api/v1/books
```

### Issue: "EPUB upload failed"

**Possible causes:**
1. EPUB file is corrupt
2. EPUB exceeds size limit (rare)
3. Network timeout

**Solution:**
```bash
# Validate EPUB locally
epubcheck path/to/book.epub

# Check file size
ls -lh path/to/book.epub
# (D2D accepts EPUBs up to 650MB)

# Retry upload (automatic retry logic included)
# If still failing, check D2D dashboard for error details
```

### Issue: "Cover upload failed"

**Possible causes:**
1. Cover dimensions too small (< 1600x2400)
2. Unsupported format
3. File too large

**Solution:**
```bash
# Check cover dimensions
file path/to/cover.jpg
# Should show at least 1600x2400 pixels

# Check format
# D2D accepts: JPEG, PNG
# Recommended: JPEG for smaller file size

# Resize if needed (requires imagemagick)
convert cover.jpg -resize 2560x1600 cover-resized.jpg
```

### Issue: Network timeout

**Solution:**
The integration includes **automatic retry logic**:
- 3 retry attempts
- Exponential backoff (2s, 4s, 8s)
- Retries on server errors (5xx) and rate limits (429)
- Does NOT retry on client errors (4xx) except rate limit

If retries fail, check:
```bash
# Test network connectivity
curl -I https://draft2digital.com

# Check for firewall/proxy issues
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

---

## Advanced Configuration

### Custom Distribution Channels

Edit `src/lily_books/tools/uploaders/draft2digital.py`:

```python
# Around line 283
DEFAULT_DISTRIBUTION = {
    "apple": True,           # Apple Books
    "kobo": True,            # Kobo
    "barnes_noble": True,    # Barnes & Noble
    "scribd": True,          # Scribd subscription
    "overdrive": True,       # Library distribution
    "tolino": True,          # EU market
    "vivlio": True,          # French market
    "palace": True,          # Library marketplace
    "bibliotheca": True,     # Library platform
    "twentyfour_symbols": False,  # Requires separate agreement
}
```

Set to `False` to disable specific retailers.

### Custom Pricing Per Territory

D2D supports territory-based pricing. To implement:

```python
# In Draft2DigitalAPI.create_book()
# Add territory_pricing parameter:

payload = {
    # ... existing fields ...
    "pricing": {
        "default": {"amount": 2.99, "currency": "USD"},
        "territories": {
            "GB": {"amount": 2.49, "currency": "GBP"},
            "EU": {"amount": 2.79, "currency": "EUR"},
        }
    }
}
```

---

## Testing

### Integration Tests

Run live API tests (requires valid API key):

```bash
# Set API key
export DRAFT2DIGITAL_API_KEY=your-api-key

# Run tests
pytest tests/test_d2d_integration.py -v --d2d-live

# WARNING: This creates real test books in your D2D account
# Delete them manually from https://draft2digital.com/books
```

### Mock Testing (No API Calls)

```bash
# Run without --d2d-live flag to use mocks
pytest tests/test_d2d_integration.py -v

# Tests initialization, error handling, etc. without API calls
```

---

## API Reference

### Draft2DigitalAPI Class

```python
from lily_books.tools.uploaders.draft2digital import Draft2DigitalAPI

# Initialize
api = Draft2DigitalAPI(api_key="your-key")

# Create book
result = api.create_book(
    title="My Book",
    authors=["Author Name"],
    description="Book description",
    keywords=["keyword1", "keyword2"],
    categories=["FIC000000"],  # BISAC codes
    price_usd=2.99,
    distribution_channels={"apple": True, "kobo": True}
)
# Returns: {"book_id": "...", "isbn": "978-...", "response": {...}}

# Upload EPUB
api.upload_manuscript(
    book_id="12345",
    epub_path=Path("path/to/book.epub")
)

# Upload cover
api.upload_cover(
    book_id="12345",
    cover_path=Path("path/to/cover.jpg")
)

# Publish
api.publish_book(book_id="12345")

# Get status
status = api.get_book_status(book_id="12345")
```

### Error Handling

All methods raise `requests.HTTPError` on failure:

```python
import requests

try:
    result = api.create_book(...)
except requests.HTTPError as e:
    print(f"API error: {e.response.status_code}")
    print(f"Details: {e.response.text}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

Automatic retries are built-in for:
- Server errors (500-599)
- Rate limits (429)
- Network timeouts

---

## Cost Analysis

### Free ISBN Value

- **Bowker ISBN:** $125 per ISBN
- **Draft2Digital ISBN:** **$0** (free)
- **Your savings:** $125 per book

### Distribution Reach

- **Retailers:** 400+ stores worldwide
- **Aggregator cost:** $0 (D2D is free)
- **Alternative (Smashwords):** $0 (also free, but fewer stores)
- **Alternative (IngramSpark):** $49 setup fee + $25/year

### Revenue Split

D2D takes **10% of net revenue** from retailers:

| Retailer | Retailer Cut | D2D Cut | Your Net |
|----------|--------------|---------|----------|
| Apple Books | 30% | 10% of 70% = 7% | 63% |
| Kobo | 30% | 10% of 70% = 7% | 63% |
| Barnes & Noble | 35% | 10% of 65% = 6.5% | 58.5% |

**Example:** $2.99 book on Apple Books
- List price: $2.99
- Apple's cut: $0.90 (30%)
- Net to publisher: $2.09
- D2D's cut: $0.21 (10% of $2.09)
- **Your revenue: $1.88 per sale**

Compare to direct Amazon KDP (70% royalty):
- $2.99 × 0.70 = $2.09 per sale

**D2D is competitive** and gives you wide distribution!

---

## Next Steps

### Batch Processing (Coming Soon)

Process multiple books at once:

```bash
# Create books.csv
# book_id,slug,price
# 1342,pride-and-prejudice,2.99
# 84,frankenstein,3.99
# 11,alice-in-wonderland,2.99

# Run batch
# poetry run python -m lily_books batch --file books.csv
```

### Sales Analytics Integration

Track sales across all retailers:

```bash
# Pull sales data from D2D API
# Aggregate with Amazon, Google Play sales
# Generate reports
```

### A/B Metadata Testing

Test different titles, descriptions, keywords:

```bash
# Upload same book with different metadata
# Track which performs better
# Optimize based on data
```

---

## FAQ

### Q: Is Draft2Digital really free?

**A:** Yes! No setup fees, no annual fees, no per-book fees. D2D takes 10% of net revenue from retailers, which is very reasonable for the wide distribution you get.

### Q: Can I use my own ISBN?

**A:** Yes, but you don't need to. D2D's free ISBN works great. If you want to use your own:
1. Purchase from Bowker (US) or your country's ISBN agency
2. Modify the uploader to use your ISBN instead of requesting one from D2D

### Q: What if I already published on Amazon?

**A:** No problem! Use the **Universal Edition** for D2D distribution. The Kindle Edition (ASIN) stays exclusive to Amazon. This is standard practice.

### Q: Can I change pricing after publishing?

**A:** Yes! Update price in D2D dashboard, changes propagate to retailers within 24-48 hours.

### Q: How do I get paid?

**A:** D2D pays quarterly (Net 90):
- Sales in Q1 → Paid in Q2 (April)
- Sales in Q2 → Paid in Q3 (July)
- Sales in Q3 → Paid in Q4 (October)
- Sales in Q4 → Paid in Q1 (January)

Minimum payment threshold: $10

### Q: Can I remove my book later?

**A:** Yes! Go to D2D dashboard → Unpublish. Book will be removed from all retailers within 1-2 weeks. Your ISBN is yours to keep forever.

---

## Support

- **Draft2Digital Support:** [https://draft2digital.com/help](https://draft2digital.com/help)
- **API Documentation:** [https://draft2digital.com/api/](https://draft2digital.com/api/)
- **lily-books Issues:** [https://github.com/nydamon/lily-books/issues](https://github.com/nydamon/lily-books/issues)

---

**Happy Publishing! 📚✨**

*Reach 400+ stores with zero upfront cost!*
