"""Sample chapter data for testing."""

from lily_books.models import ChapterSplit, ChapterDoc, ParaPair, QAReport


def get_sample_chapter_split() -> ChapterSplit:
    """Get a sample ChapterSplit for testing."""
    return ChapterSplit(
        chapter=1,
        title="Chapter 1",
        paragraphs=[
            "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.",
            '"My dear Mr. Bennet," said his lady to him one day, "have you heard that Netherfield Park is let at last?"',
            "However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters.",
            "_Pride and Prejudice_, by Jane Austen"
        ]
    )


def get_sample_chapter_doc() -> ChapterDoc:
    """Get a sample ChapterDoc for testing."""
    pairs = [
        ParaPair(
            i=0,
            para_id="ch01_para000",
            orig="It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.",
            modern="It is a truth universally acknowledged that a single man with a good fortune must be looking for a wife.",
            qa=QAReport(
                fidelity_score=95,
                readability_grade=8.0,
                character_count_ratio=1.1,
                modernization_complete=True,
                formatting_preserved=True,
                tone_consistent=True,
                quote_count_match=True,
                emphasis_preserved=True
            )
        ),
        ParaPair(
            i=1,
            para_id="ch01_para001",
            orig='"My dear Mr. Bennet," said his lady to him one day, "have you heard that Netherfield Park is let at last?"',
            modern='"My dear Mr. Bennet," said his wife to him one day, "have you heard that Netherfield Park is rented at last?"',
            qa=QAReport(
                fidelity_score=92,
                readability_grade=7.5,
                character_count_ratio=1.05,
                modernization_complete=True,
                formatting_preserved=True,
                tone_consistent=True,
                quote_count_match=True,
                emphasis_preserved=True
            )
        ),
        ParaPair(
            i=2,
            para_id="ch01_para002",
            orig="However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters.",
            modern="However little known the feelings or views of such a man may be when he first enters a neighborhood, this truth is so well fixed in the minds of the surrounding families that he is considered the rightful property of someone or other of their daughters.",
            qa=QAReport(
                fidelity_score=88,
                readability_grade=8.5,
                character_count_ratio=1.15,
                modernization_complete=True,
                formatting_preserved=True,
                tone_consistent=True,
                quote_count_match=True,
                emphasis_preserved=True
            )
        ),
        ParaPair(
            i=3,
            para_id="ch01_para003",
            orig="_Pride and Prejudice_, by Jane Austen",
            modern="_Pride and Prejudice_, by Jane Austen",
            qa=QAReport(
                fidelity_score=100,
                readability_grade=8.0,
                character_count_ratio=1.0,
                modernization_complete=True,
                formatting_preserved=True,
                tone_consistent=True,
                quote_count_match=True,
                emphasis_preserved=True
            )
        )
    ]
    
    return ChapterDoc(
        chapter=1,
        title="Chapter 1",
        pairs=pairs
    )


def get_sample_text() -> str:
    """Get sample text for testing chapterization."""
    return """
CHAPTER 1

It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.

However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters.

"My dear Mr. Bennet," said his lady to him one day, "have you heard that Netherfield Park is let at last?"

CHAPTER 2

Mr. Bennet was among the earliest of those who waited on Mr. Bingley.

He had always intended to visit him, though to the last always assuring his wife that he should not go; and till the evening after the visit was paid she had no knowledge of it.
"""

