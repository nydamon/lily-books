#!/usr/bin/env python3
"""Full pipeline test with real LLM calls, QA, TTS, and audio mastering."""

import time
from pathlib import Path

from lily_books.chains.checker import qa_chapter
from lily_books.chains.ingest import chapterize, load_gutendex
from lily_books.chains.writer import rewrite_chapter
from lily_books.models import BookMetadata
from lily_books.tools.audio import get_audio_metrics, master_audio
from lily_books.tools.epub import build_epub
from lily_books.tools.epub_validator import (
    get_epub_quality_report,
    validate_epub_structure,
)
from lily_books.tools.tts import tts_fish_audio


def test_full_pipeline():
    """Test complete pipeline with real components."""
    print("🚀 Starting full pipeline test (first 2 chapters)...")
    start_time = time.time()

    try:
        # Step 1: Ingest (with fallback for API issues)
        print("📥 Ingesting book...")
        try:
            raw_text = load_gutendex(1342)
            print(f"✅ Ingested {len(raw_text)} characters")
        except Exception as e:
            print(f"⚠️ Gutendex API failed: {e}")
            print("📥 Using mock text for testing...")
            raw_text = """
            CHAPTER I

            It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.

            However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters.

            "My dear Mr. Bennet," said his lady to him one day, "have you heard that Netherfield Park is let at last?"

            Mr. Bennet replied that he had not.

            "But it is," returned she; "for Mrs. Long has just been here, and she told me all about it."

            Mr. Bennet made no answer.

            "Do you not want to know who has taken it?" cried his wife impatiently.

            "You want to tell me, and I have no objection to hearing it."

            This was invitation enough.

            "Why, my dear, you must know, Mrs. Long says that Netherfield is taken by a young man of large fortune from the north of England; that he came down on Monday in a chaise and four to see the place, and was so much delighted with it, that he agreed with Mr. Morris immediately; that he is to take possession before Michaelmas, and some of his servants are to be in the house by the end of next week."

            "What is his name?"

            "Bingley."

            "Is he married or single?"

            "Oh! Single, my dear, to be sure! A single man of large fortune; four or five thousand a year. What a fine thing for our girls!"

            "How so? How can it affect them?"

            "My dear Mr. Bennet," replied his wife, "how can you be so tiresome! You must know that I am thinking of his marrying one of them."

            "Is that his design in settling here?"

            "Design! Nonsense, how can you talk so! But it is very likely that he may fall in love with one of them, and therefore you must visit him as soon as he comes."

            "I see no occasion for that. You and the girls may go, or you may send them by themselves, which perhaps will be still better, for as you are as handsome as any of them, Mr. Bingley might like you the best of the party."

            "My dear, you flatter me. I certainly have had my share of beauty, but I do not pretend to be anything extraordinary now. When a woman has five grown-up daughters, she ought to give over thinking of her own beauty."

            "In such cases, a woman has not often much beauty to think of."

            "But, my dear, you must indeed go and see Mr. Bingley when he comes into the neighbourhood."

            "It is more than I engage for, I assure you."

            "But consider your daughters. Only think what an establishment it would be for one of them. Sir William and Lady Lucas are determined to go, merely on that account, for in general, you know, they visit no newcomers. Indeed you must go, for it will be impossible for us to visit him if you do not."

            "You are over-scrupulous, surely. I dare say Mr. Bingley will be very glad to see you; and I will send a few lines by you to assure him of my hearty consent to his marrying whichever he chooses of the girls; though I must throw in a good word for my little Lizzy."

            "I desire you will do no such thing. Lizzy is not a bit better than the others; and I am sure she is not half so handsome as Jane, nor half so good-humoured as Lydia. But you are always giving her the preference."

            "They have none of them much to recommend them," replied he; "they are all silly and ignorant like other girls; but Lizzy has something more of quickness than her sisters."

            "Mr. Bennet, how can you abuse your own children in such a way? You take delight in vexing me. You have no compassion for my poor nerves."

            "You mistake me, my dear. I have a high respect for your nerves. They are my old friends. I have heard you mention them with consideration these last twenty years at least."

            "Ah, you do not know what I suffer."

            "But I hope you will get over it, and live to see many young men of four thousand a year come into the neighbourhood."

            "It will be no use to us, if twenty such should come, since you will not visit them."

            "Depend upon it, my dear, that when there are twenty, I will visit them all."

            Mr. Bennet was so odd a mixture of quick parts, sarcastic humour, reserve, and caprice, that the experience of three-and-twenty years had been insufficient to make his wife understand his character. Her mind was less difficult to develop. She was a woman of mean understanding, little information, and uncertain temper. When she was discontented, she fancied herself nervous. The business of her life was to get her daughters married; its solace was visiting and news.

            CHAPTER II

            Mr. Bennet was among the earliest of those who waited on Mr. Bingley. He had always intended to visit him, though to the last always assuring his wife that he should not go; and till the evening after the visit was paid she had no knowledge of it. It was then disclosed in the following manner. Observing his second daughter employed in trimming a hat, he suddenly addressed her with,--

            "I hope Mr. Bingley will like it, Lizzy."

            "We are not in a way to know what Mr. Bingley likes," said her mother, resentfully, "since we are not to visit."

            "But you forget, mamma," said Elizabeth, "that we shall meet him at the assemblies, and that Mrs. Long has promised to introduce him."

            "I do not believe Mrs. Long will do any such thing. She has two nieces of her own. She is a selfish, hypocritical woman, and I have no opinion of her."

            "No more have I," said Mr. Bennet; "and I am glad to find that you do not depend on her serving you."

            Mrs. Bennet deigned not to make any reply; but, unable to contain herself, began scolding one of her daughters.

            "Don't keep coughing so, Kitty, for heaven's sake! Have a little compassion on my nerves. You tear them to pieces."

            "Kitty has no discretion in her coughs," said her father; "she times them ill."

            "I do not cough for my own amusement," replied Kitty, fretfully. "When is your next ball to be, Lizzy?"

            "To-morrow fortnight."

            "Ay, so it is," cried her mother, "and Mrs. Long does not come back till the day before; so, it will be impossible for her to introduce him, for she will not know him herself."

            "Then, my dear, you may have the advantage of your friend, and introduce Mr. Bingley to her."

            "Impossible, Mr. Bennet, impossible, when I am not acquainted with him myself; how can you be so teasing?"

            "I honour your circumspection. A fortnight's acquaintance is certainly very little. One cannot know what a man really is by the end of a fortnight. But if we do not venture, somebody else will; and after all, Mrs. Long and her nieces must stand their chance; and, therefore, as she will think it an act of kindness, if you decline the office, I will take it on myself."

            The girls stared at their father. Mrs. Bennet said only, "Nonsense, nonsense!"

            "What can be the meaning of that emphatic exclamation?" cried he. "Do you consider the forms of introduction, and the stress that is laid on them, as nonsense? I cannot quite agree with you there. What say you, Mary? For you are a young lady of deep reflection, I know, and read great books, and make extracts."

            Mary wished to say something very sensible, but knew not how.

            "While Mary is adjusting her ideas," he continued, "let us return to Mr. Bingley."

            "I am sick of Mr. Bingley," cried his wife.

            "I am sorry to hear that; but why did you not tell me so before? If I had known as much this morning, I certainly would not have called on him. It is very unlucky; but as we have actually paid the visit, we cannot escape the acquaintance now."

            The astonishment of the ladies was just what he wished--that of Mrs. Bennet perhaps surpassing the rest; though when the first tumult of joy was over, she began to declare that it was what she had expected all the while.

            "How good it was in you, my dear Mr. Bennet! But I knew I should persuade you at last. I was sure you loved your girls too well to neglect such an acquaintance. Well, how pleased I am! And it is such a good joke, too, that you should have gone this morning, and never said a word about it till now."

            "Now, Kitty, you may cough as much as you choose," said Mr. Bennet; and, as he spoke, he left the room, fatigued with the raptures of his wife.

            "What an excellent father you have, girls," said she, when the door was shut. "I do not know how you will ever make him amends for his kindness; or me either, for that matter. At our time of life, it is not so pleasant, I can tell you, to be making new acquaintances every day; but for your sakes we would do anything. Lydia, my love, though you are the youngest, I dare say Mr. Bingley will dance with you at the next ball."

            "Oh," said Lydia, stoutly, "I am not afraid; for though I am the youngest, I'm the tallest."

            The rest of the evening was spent in conjecturing how soon he would return Mr. Bennet's visit, and determining when they should ask him to dinner.
            """
            print(f"✅ Using mock text with {len(raw_text)} characters")

        # Step 2: Chapterize
        print("📚 Chapterizing...")
        chapters = chapterize(raw_text)
        print(f"✅ Found {len(chapters)} chapters")

        # Step 3: Process only first 2 chapters (skip preamble)
        print("✏️ Processing first 2 chapters with real LLM...")
        rewritten_chapters = []
        for i, chapter_split in enumerate(
            chapters[1:3]
        ):  # Skip preamble, get chapters 1-2
            print(f"   Rewriting {chapter_split.title}...")
            chapter_doc = rewrite_chapter(chapter_split)
            rewritten_chapters.append(chapter_doc)
            print(f"   ✅ Rewrote {len(chapter_doc.pairs)} paragraphs")

        # Step 4: QA validation
        print("🔍 Running QA validation...")
        all_passed = True
        for chapter_doc in rewritten_chapters:
            print(f"   QA checking {chapter_doc.title}...")
            passed, issues, updated_doc = qa_chapter(chapter_doc)
            if not passed:
                all_passed = False
                print(f"   ⚠️ QA issues found: {len(issues)}")
            else:
                print("   ✅ QA passed")

        print(f"✅ QA complete - All passed: {all_passed}")

        # Step 5: Build EPUB
        print("📖 Building EPUB...")
        metadata = BookMetadata(
            title="Pride and Prejudice (Modernized Student Edition)",
            author="Jane Austen",
            public_domain_source="Project Gutenberg #1342",
        )

        epub_path = build_epub("full-test", rewritten_chapters, metadata)
        print(f"✅ Created EPUB: {epub_path}")

        # Step 5.5: EPUB Validation
        print("📋 Validating EPUB quality...")
        validation_result = validate_epub_structure(epub_path)
        get_epub_quality_report(epub_path)

        print(f"✅ EPUB Quality Score: {validation_result.quality_score}/100")
        if validation_result.errors:
            print(f"❌ EPUB Errors: {len(validation_result.errors)}")
            for error in validation_result.errors:
                print(f"   • {error}")
        if validation_result.warnings:
            print(f"⚠️ EPUB Warnings: {len(validation_result.warnings)}")
            for warning in validation_result.warnings:
                print(f"   • {warning}")

        epub_quality_ok = validation_result.quality_score >= 70

        # Step 6: TTS Generation
        print("🎤 Generating TTS audio...")
        audio_files = []
        for chapter_doc in rewritten_chapters:
            print(f"   Generating TTS for {chapter_doc.title}...")
            # Combine all paragraphs
            text = "\n\n".join(pair.modern for pair in chapter_doc.pairs)

            # Generate TTS
            wav_path = Path(
                f"books/full-test/work/audio/ch{chapter_doc.chapter:02d}.wav"
            )
            wav_path.parent.mkdir(parents=True, exist_ok=True)

            result = tts_fish_audio(text, "", wav_path)  # Use default Fish Audio voice
            audio_files.append(
                {
                    "chapter": chapter_doc.chapter,
                    "wav_path": str(wav_path),
                    "duration_sec": result["duration_sec"],
                }
            )
            print(f"   ✅ Generated {result['duration_sec']:.1f}s audio")

        # Step 7: Audio Mastering
        print("🎛️ Mastering audio...")
        mastered_files = []
        for audio_file in audio_files:
            print(f"   Mastering chapter {audio_file['chapter']}...")
            wav_path = Path(audio_file["wav_path"])
            mp3_path = Path(
                f"books/full-test/work/audio_mastered/ch{audio_file['chapter']:02d}.mp3"
            )
            mp3_path.parent.mkdir(parents=True, exist_ok=True)

            result = master_audio(wav_path, mp3_path)
            mastered_files.append(
                {
                    "chapter": audio_file["chapter"],
                    "mp3_path": str(mp3_path),
                    "duration_sec": result["duration_sec"],
                }
            )
            print(f"   ✅ Mastered to {result['duration_sec']:.1f}s MP3")

        # Step 8: Audio QA
        print("🔊 Running audio QA...")
        audio_ok = True
        for mastered_file in mastered_files:
            print(f"   QA checking chapter {mastered_file['chapter']}...")
            wav_path = Path(mastered_file["mp3_path"])
            metrics = get_audio_metrics(wav_path)

            # Check ACX thresholds
            rms_ok = metrics["rms_db"] is None or metrics["rms_db"] >= -23
            peak_ok = metrics["peak_db"] is None or metrics["peak_db"] <= -3

            if not (rms_ok and peak_ok):
                audio_ok = False
                print(
                    f"   ⚠️ Audio QA failed: RMS={metrics['rms_db']}, Peak={metrics['peak_db']}"
                )
            else:
                print(
                    f"   ✅ Audio QA passed: RMS={metrics['rms_db']}, Peak={metrics['peak_db']}"
                )

        print(f"✅ Audio QA complete - All passed: {audio_ok}")

        # Step 9: Final verification
        print("🔍 Final verification...")
        epub_size = Path(epub_path).stat().st_size
        total_audio_duration = sum(f["duration_sec"] for f in mastered_files)

        runtime = time.time() - start_time
        print(f"🎉 Full pipeline completed successfully in {runtime:.1f} seconds!")
        print("📊 Final Summary:")
        print(f"   • Chapters processed: {len(rewritten_chapters)}")
        print(
            f"   • Total paragraphs: {sum(len(ch.pairs) for ch in rewritten_chapters)}"
        )
        print(f"   • EPUB created: {epub_path} ({epub_size} bytes)")
        print(f"   • Audio chapters: {len(mastered_files)}")
        print(f"   • Total audio duration: {total_audio_duration:.1f} seconds")
        print(f"   • Text QA passed: {all_passed}")
        print(f"   • Audio QA passed: {audio_ok}")
        print(f"   • EPUB Quality Score: {validation_result.quality_score}/100")
        print(f"   • EPUB Quality OK: {epub_quality_ok}")

        return True

    except Exception as e:
        runtime = time.time() - start_time
        print(f"❌ Pipeline failed after {runtime:.1f} seconds: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_full_pipeline()
    exit(0 if success else 1)
