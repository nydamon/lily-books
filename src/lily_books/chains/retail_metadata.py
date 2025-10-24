"""Enhanced metadata generation for retail distribution.

Generates SEO-optimized metadata for maximum discoverability on:
- Amazon KDP
- Google Play Books
- Apple Books (via Draft2Digital)
"""

from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from lily_books.models import FlowState, RetailMetadata
from lily_books.utils.llm_factory import create_llm_with_fallback


# BISAC category reference
BISAC_CATEGORIES = {
    "classics": {
        "FIC004000": "Fiction / Classics",
        "FIC019000": "Fiction / Literary",
        "FIC027050": "Fiction / Romance / Historical / General",
    },
    "education": {
        "EDU029010": "Education / Teaching Methods & Materials / Arts & Humanities",
        "STU004000": "Study Aids / Book Notes",
        "FOR007000": "Foreign Language Study / English as a Second Language",
    },
    "age_appropriate": {
        "YAF024000": "Young Adult Fiction / Classics",
        "JUV014000": "Juvenile Fiction / Classics",
    },
}


class RetailMetadataGenerator:
    """Generates AI-optimized metadata for maximum discoverability."""

    def __init__(self):
        self.llm = create_llm_with_fallback(
            provider="openai",
            temperature=0.7,
        )
        self.parser = JsonOutputParser(pydantic_object=RetailMetadata)

    def generate_metadata(self, state: FlowState) -> FlowState:
        """Generate SEO-optimized metadata for retail distribution."""

        # Extract existing metadata
        pub_meta = state.get("publishing_metadata", {})
        original_title = pub_meta.get("title", "Untitled")
        author = pub_meta.get("original_author", "Unknown")
        modernized_author = pub_meta.get("author", author)

        # Get sample text for context
        sample_text = self._extract_sample_text(state)

        # Get pricing info if available
        pricing = state.get("pricing", {})
        price = pricing.get("base_price_usd", 2.99)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert book marketing strategist specializing in
metadata optimization for Amazon, Google Play, and Apple Books.

Your goal: Maximize discoverability through SEO-rich, compelling metadata
that appeals to:
1. Students assigned classic literature
2. Teachers looking for accessible editions
3. ESL learners
4. Adult readers intimidated by archaic English
5. Lifelong learners

Emphasize:
- "Modernized" / "Modern English" / "Accessible"
- Educational value
- Preservation of original meaning
- Student-friendly
- Clear, contemporary language

Output format: {format_instructions}
""",
                ),
                (
                    "human",
                    """Generate metadata for this modernized classic edition:

Original Title: {original_title}
Author: {author}
Modernized by: {modernized_author}

Our Edition: "{modern_title}"

Sample modernized text (first paragraph):
{sample_text}

Target price point: ${price}
Primary retailers: Amazon KDP, Google Play Books, Apple Books

Research shows readers search for:
- "[classic title] easy to read"
- "[classic title] modern English"
- "[classic title] for students"
- "accessible classics"
- "[author] simplified"

Create metadata that captures these search intents while maintaining
literary prestige and educational credibility.

Requirements:
- title_variations: 3 compelling title variations for A/B testing
- subtitle: Compelling subtitle under 200 chars
- description_short: 150-char elevator pitch for search results
- description_long: 800-1500 word detailed description with HTML formatting
- keywords: 20 SEO keywords customers actually search
- bisac_categories: 3-5 BISAC codes (use FIC004000 for Classics)
- amazon_keywords: 7 keywords specific to Amazon search
- comp_titles: 5 competitive/comparable titles
""",
                ),
            ]
        )

        chain = prompt | self.llm | self.parser

        try:
            metadata_dict = chain.invoke(
                {
                    "format_instructions": self.parser.get_format_instructions(),
                    "original_title": original_title,
                    "author": author,
                    "modernized_author": modernized_author,
                    "modern_title": original_title,
                    "sample_text": sample_text[:500],
                    "price": price,
                }
            )

            if isinstance(metadata_dict, RetailMetadata):
                retail_metadata = metadata_dict
            else:
                retail_metadata = RetailMetadata(**metadata_dict)

            state["retail_metadata"] = retail_metadata.model_dump()

            print(f"\n✓ Generated SEO metadata:")
            print(f"  - Title variations: {len(retail_metadata.title_variations)}")
            print(f"  - Keywords: {len(retail_metadata.keywords)}")
            print(f"  - Amazon keywords: {len(retail_metadata.amazon_keywords)}")
            print(f"  - BISAC categories: {len(retail_metadata.bisac_categories)}")
            print(f"  - Description length: {len(retail_metadata.description_long)} chars")
            print(f"  - Comparative titles: {len(retail_metadata.comp_titles)}\n")

            return state

        except Exception as e:
            print(f"⚠ Metadata generation failed, using fallback: {e}")
            # Fallback to basic metadata
            fallback_metadata = self._generate_fallback_metadata(state)
            state["retail_metadata"] = fallback_metadata.model_dump()
            return state

    def _extract_sample_text(self, state: FlowState) -> str:
        """Extract sample text from first chapter."""
        rewritten = state.get("rewritten") or []
        if rewritten:
            first_chapter = rewritten[0]
            pairs = getattr(first_chapter, "pairs", None)
            if pairs is None and isinstance(first_chapter, dict):
                pairs = first_chapter.get("pairs")

            if pairs:
                first_pair = pairs[0]
                modern_text = getattr(first_pair, "modern", None)
                if modern_text is None and isinstance(first_pair, dict):
                    modern_text = first_pair.get("modern")

                if modern_text:
                    return modern_text

        return "A modernized edition of a classic work of literature."

    def _generate_fallback_metadata(self, state: FlowState) -> RetailMetadata:
        """Generate basic fallback metadata if AI generation fails."""
        pub_meta = state.get("publishing_metadata", {})
        title = pub_meta.get("title", "Untitled")
        author = pub_meta.get("original_author", "Unknown")

        return RetailMetadata(
            title_variations=[
                f"{title}",
                f"{title}: A Modern English Edition",
                f"{title} (Modernized Classic)",
            ],
            subtitle="A Modernized Edition for Contemporary Readers",
            description_short=f"Experience {author}'s timeless classic in clear, modern English that preserves the original meaning and style.",
            description_long=f"""<h2>About This Edition</h2>

<p>This modernized edition of {title} by {author} brings this timeless classic to contemporary readers through careful language modernization. While preserving the original plot, characters, and literary style, we've updated archaic vocabulary and complex sentence structures to make this masterpiece more accessible.</p>

<h3>Why Choose This Edition?</h3>

<ul>
<li><strong>Modern English:</strong> Updated language for easier comprehension</li>
<li><strong>Faithful Adaptation:</strong> Original meaning and style preserved</li>
<li><strong>Student-Friendly:</strong> Perfect for school assignments and study</li>
<li><strong>ESL-Accessible:</strong> Clear language for English learners</li>
</ul>

<p>Whether you're a student tackling classic literature for the first time or a lifelong reader seeking a more accessible experience, this edition offers the perfect balance of literary quality and modern readability.</p>

<p>Join thousands of readers rediscovering {author}'s masterpiece in this acclaimed modernized edition.</p>
""",
            keywords=[
                f"{title.lower()} modern english",
                f"{title.lower()} easy to read",
                f"{title.lower()} for students",
                f"{author.lower()} accessible",
                "modernized classics",
                "classic literature easy",
                "student friendly classics",
                f"{title.lower()} simplified",
            ],
            bisac_categories=["FIC004000", "EDU029010", "FIC019000"],
            amazon_keywords=[
                f"{title.lower()} modern",
                "accessible classics",
                f"{author.lower()} easy",
                "student edition",
                "modernized literature",
                "classic books easy",
                "esl classics",
            ],
            comp_titles=[],
        )


def generate_retail_metadata_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for retail metadata generation."""
    generator = RetailMetadataGenerator()
    state = generator.generate_metadata(state)

    return {"retail_metadata": state["retail_metadata"]}
