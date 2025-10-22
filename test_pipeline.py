#!/usr/bin/env python3
"""Full pipeline test with real-time monitoring."""

import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Setup logging to console with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Enable debug for our modules
logging.getLogger('src.lily_books').setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Import after logging setup
from src.lily_books.runner import run_pipeline_async
from src.lily_books.config import settings

print("=" * 80)
print("FULL PIPELINE TEST - REAL-TIME MONITORING")
print("=" * 80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
print("Configuration:")
print(f"  Anthropic model:   {settings.anthropic_model}")
print(f"  OpenAI model:      {settings.openai_model}")
print(f"  Cache enabled:     {settings.cache_enabled}")
print(f"  Langfuse enabled:  {settings.langfuse_enabled}")
print(f"  Max retries:       {settings.max_retry_attempts}")
print("=" * 80)
print()

async def monitor_pipeline():
    """Run pipeline with monitoring."""

    # Test with a very small book for quick validation
    # Project Gutenberg #1342 = Pride and Prejudice (good test, has ~60 chapters)
    # For quick test, we'll limit to just chapter 1

    slug = "pipeline-test"
    book_id = 1342
    chapters = [1]  # Just test chapter 1

    logger.info(f"Starting pipeline test: slug={slug}, book_id={book_id}, chapters={chapters}")

    start_time = time.time()

    try:
        # Run async pipeline
        logger.info("Invoking run_pipeline_async...")
        result = await run_pipeline_async(
            slug=slug,
            book_id=book_id,
            chapters=chapters  # Only parameter is chapters, rest handled by state
        )

        elapsed = time.time() - start_time

        print()
        print("=" * 80)
        print("PIPELINE TEST RESULTS")
        print("=" * 80)
        print(f"Status: {'✅ SUCCESS' if result else '❌ FAILED'}")
        print(f"Duration: {elapsed:.1f}s")
        print()

        if result:
            print("Pipeline completed successfully!")
            print(f"\nResult keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

            # Check for expected outputs
            if isinstance(result, dict):
                if result.get('rewritten'):
                    print(f"✅ Chapters rewritten: {len(result['rewritten'])}")
                if result.get('qa_text_ok'):
                    print(f"✅ QA validation: PASSED")
                else:
                    print(f"⚠️  QA validation: FAILED or not run")

                if 'epub_path' in result and result['epub_path']:
                    print(f"✅ EPUB generated: {result['epub_path']}")
        else:
            print("❌ Pipeline returned no result")

        print("=" * 80)

        return result

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        raise
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Pipeline failed after {elapsed:.1f}s: {e}", exc_info=True)
        print()
        print("=" * 80)
        print("❌ PIPELINE FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print(f"Duration: {elapsed:.1f}s")
        print("=" * 80)
        raise

if __name__ == "__main__":
    try:
        result = asyncio.run(monitor_pipeline())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        sys.exit(1)
