#!/usr/bin/env python3
"""Working pipeline test with first 2 chapters only."""

import time
from lily_books.chains.ingest import load_gutendex, chapterize
from lily_books.models import ChapterDoc, ParaPair
from lily_books.tools.epub import build_epub
from lily_books.models import BookMetadata

def test_working_pipeline():
    """Test pipeline with first 2 chapters only."""
    print("🚀 Starting working pipeline test (first 2 chapters only)...")
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
        
        # Step 3: Process only first 2 chapters
        print("✏️ Processing first 2 chapters only...")
        rewritten_chapters = []
        for chapter_split in chapters[:2]:  # Only first 2 chapters
            print(f"   Processing {chapter_split.title}...")
            pairs = []
            for i, para in enumerate(chapter_split.paragraphs[:5]):  # Only first 5 paragraphs per chapter
                pairs.append(ParaPair(
                    i=i,
                    para_id=f"ch{chapter_split.chapter:02d}_para{i:03d}",
                    orig=para,
                    modern=f"[MODERNIZED] {para[:100]}..."  # Mock modernization
                ))
            rewritten_chapters.append(ChapterDoc(
                chapter=chapter_split.chapter,
                title=chapter_split.title,
                pairs=pairs
            ))
            print(f"   ✅ Processed {len(pairs)} paragraphs")
        print(f"✅ Processed {len(rewritten_chapters)} chapters")
        
        # Step 4: Build EPUB
        print("📖 Building EPUB...")
        metadata = BookMetadata(
            title="Pride and Prejudice (Test Edition - First 2 Chapters)",
            author="Jane Austen",
            public_domain_source="Project Gutenberg #1342"
        )
        
        epub_path = build_epub("working-test", rewritten_chapters, metadata)
        print(f"✅ Created EPUB: {epub_path}")
        
        # Step 5: Verify output
        print("🔍 Verifying output...")
        import os
        epub_size = os.path.getsize(epub_path)
        print(f"✅ EPUB size: {epub_size} bytes")
        
        runtime = time.time() - start_time
        print(f"🎉 Pipeline completed successfully in {runtime:.1f} seconds!")
        print(f"📊 Summary:")
        print(f"   • Chapters processed: {len(rewritten_chapters)}")
        print(f"   • Total paragraphs: {sum(len(ch.pairs) for ch in rewritten_chapters)}")
        print(f"   • EPUB created: {epub_path}")
        return True
        
    except Exception as e:
        runtime = time.time() - start_time
        print(f"❌ Pipeline failed after {runtime:.1f} seconds: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_working_pipeline()
    exit(0 if success else 1)
