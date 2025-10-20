#!/usr/bin/env python3
"""Test EPUB validation in the pipeline."""

import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
import sys
sys.path.append(str(Path(__file__).parent))

from lily_books.runner import run_pipeline
from lily_books.models import ChapterDoc, ParaPair, QAReport, ChapterSplit, BookMetadata
from lily_books.config import get_project_paths, ensure_directories

# Mock rewrite_chapter and qa_chapter for a minimal test
def mock_rewrite_chapter(ch: ChapterSplit) -> ChapterDoc:
    pairs = []
    for i, para in enumerate(ch.paragraphs):
        pairs.append(ParaPair(
            i=i,
            para_id=f"ch{ch.chapter:02d}_para{i:03d}",
            orig=para,
            modern=f"Modernized: {para}"
        ))
    return ChapterDoc(chapter=ch.chapter, title=ch.title, pairs=pairs)

def mock_qa_chapter(doc: ChapterDoc, fidelity_threshold: int = 92):
    for pair in doc.pairs:
        pair.qa = QAReport(
            fidelity_score=95,
            readability_grade=8.0,
            character_count_ratio=1.1,
            modernization_complete=True,
            formatting_preserved=True,
            tone_consistent=True,
            quote_count_match=True,
            emphasis_preserved=True
        )
    return True, [], doc

def test_epub_validation():
    """Test EPUB validation in the pipeline."""
    slug = "epub-test"
    book_id = 1342 # Pride and Prejudice
    
    print("🚀 Starting EPUB validation test...")
    start_time = time.time()
    
    # Clean up previous run
    paths = get_project_paths(slug)
    if paths["base"].exists():
        import shutil
        shutil.rmtree(paths["base"])
    ensure_directories(slug)
    
    with patch('src.lily_books.chains.writer.rewrite_chapter', side_effect=mock_rewrite_chapter), \
         patch('src.lily_books.chains.checker.qa_chapter', side_effect=mock_qa_chapter), \
         patch('src.lily_books.tools.tts.tts_elevenlabs') as mock_tts, \
         patch('src.lily_books.tools.audio.master_audio') as mock_master, \
         patch('src.lily_books.tools.audio.get_audio_metrics') as mock_metrics, \
         patch('src.lily_books.chains.ingest.load_gutendex', return_value="""
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
"""):
        
        # Configure mocks
        mock_tts.return_value = {"wav": "mock.wav", "duration_sec": 1.0, "chunks_processed": 1}
        mock_master.return_value = {"mp3": "mock.mp3", "duration_sec": 1.0, "target_rms_db": -20}
        mock_metrics.return_value = {"rms_db": -20, "peak_db": -5, "duration_sec": 1.0}
        
        # Run pipeline for first 2 chapters
        result = run_pipeline(slug, book_id, chapters=[0, 1])
        
        runtime = time.time() - start_time
        print(f"🎉 Pipeline completed successfully in {runtime:.1f} seconds!")
        
        # Check EPUB validation results
        assert result["success"] is True
        assert "epub_quality_score" in result["deliverables"]
        
        quality_score = result["deliverables"]["epub_quality_score"]
        print(f"✅ EPUB Quality Score: {quality_score}/100")
        
        assert quality_score >= 70, f"EPUB quality score {quality_score} is below threshold"
        
        # Verify EPUB file exists and has good size
        epub_path = Path(result["deliverables"]["epub_path"])
        assert epub_path.exists()
        epub_size = epub_path.stat().st_size
        print(f"✅ EPUB size: {epub_size} bytes")
        assert epub_size > 4000, f"EPUB too small: {epub_size} bytes"
        
        print("\n📊 Summary:")
        print(f"   • Chapters processed: {len(result['rewritten'])}")
        print(f"   • Total paragraphs: {sum(len(ch.pairs) for ch in result['rewritten'])}")
        print(f"   • EPUB created: {epub_path}")
        print(f"   • EPUB Quality Score: {quality_score}/100")
        print(f"   • Audio chapters: {result['deliverables']['audio_chapters']}")
        
        return True

if __name__ == "__main__":
    test_epub_validation()
