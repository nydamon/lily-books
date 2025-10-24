#!/usr/bin/env python3
"""Minimal pipeline test that skips LLM calls."""

import time

from lily_books.chains.ingest import chapterize, load_gutendex
from lily_books.models import BookMetadata, ChapterDoc, ParaPair
from lily_books.tools.epub import build_epub


def test_minimal_pipeline():
    """Test pipeline with mocked LLM responses."""
    print("🚀 Starting minimal pipeline test...")
    start_time = time.time()

    try:
        # Step 1: Ingest
        print("📥 Ingesting book...")
        raw_text = load_gutendex(1342)
        print(f"✅ Ingested {len(raw_text)} characters")

        # Step 2: Chapterize
        print("📚 Chapterizing...")
        chapters = chapterize(raw_text)
        print(f"✅ Found {len(chapters)} chapters")

        # Step 3: Mock rewrite (skip LLM)
        print("✏️ Mock rewriting...")
        rewritten_chapters = []
        for chapter_split in chapters[:2]:  # Only process first 2 chapters
            pairs = []
            for i, para in enumerate(
                chapter_split.paragraphs[:3]
            ):  # Only first 3 paragraphs
                pairs.append(
                    ParaPair(
                        i=i,
                        para_id=f"ch{chapter_split.chapter:02d}_para{i:03d}",
                        orig=para,
                        modern=f"[MODERNIZED] {para[:50]}...",  # Mock modernization
                    )
                )
            rewritten_chapters.append(
                ChapterDoc(
                    chapter=chapter_split.chapter,
                    title=chapter_split.title,
                    pairs=pairs,
                )
            )
        print(f"✅ Rewrote {len(rewritten_chapters)} chapters")

        # Step 4: Build EPUB
        print("📖 Building EPUB...")
        metadata = BookMetadata(
            title="Pride and Prejudice (Test Edition)",
            author="Jane Austen",
            public_domain_source="Project Gutenberg #1342",
        )

        epub_path = build_epub("test-book", rewritten_chapters, metadata)
        print(f"✅ Created EPUB: {epub_path}")

        runtime = time.time() - start_time
        print(f"🎉 Pipeline completed in {runtime:.1f} seconds!")
        return True

    except Exception as e:
        runtime = time.time() - start_time
        print(f"❌ Pipeline failed after {runtime:.1f} seconds: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_minimal_pipeline()
    exit(0 if success else 1)
