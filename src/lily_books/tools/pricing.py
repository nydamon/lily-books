"""Pricing optimization for ebook distribution.

Calculates optimal price points based on:
- Page/word count
- Competitive pricing
- Retailer royalty structures
"""

from typing import Any

from lily_books.models import FlowState, PricingInfo


class PricingOptimizer:
    """Calculates optimal pricing across retailers."""

    # Royalty tiers
    AMAZON_ROYALTY_TIERS = {
        "35%": {"min": 0.99, "max": 200.0, "rate": 0.35},
        "70%": {
            "min": 2.99,
            "max": 9.99,
            "rate": 0.70,
            "delivery_fee_per_mb": 0.15,
        },
    }

    GOOGLE_ROYALTY_RATE = 0.52  # ~52% after Google's cut
    APPLE_VIA_D2D_RATE = 0.60  # ~60% (Apple 70% - D2D 10%)

    def calculate_optimal_pricing(self, state: FlowState) -> FlowState:
        """
        Calculate optimal price points based on book characteristics.

        Strategy:
        1. Determine base price from word count
        2. Ensure 70% Amazon royalty tier (>= $2.99)
        3. Apply same price across all retailers for simplicity
        """
        # Extract book characteristics
        word_count = self._estimate_word_count(state)
        page_count = word_count // 250  # Rough estimate

        # Pricing logic based on length
        if page_count < 150:
            base_price = 0.99
        elif page_count < 250:
            base_price = 2.99
        elif page_count < 400:
            base_price = 3.99
        else:
            base_price = 4.99

        # Ensure 70% royalty tier on Amazon
        if base_price < 2.99:
            recommended_price = 2.99
            reason = "Increased to $2.99 to qualify for Amazon 70% royalty tier"
        else:
            recommended_price = base_price
            reason = f"Based on {page_count} estimated pages (~{word_count:,} words)"

        # Override with config default if set
        from lily_books.config import settings

        if settings.default_price_usd > 0:
            recommended_price = settings.default_price_usd
            reason = f"Using configured default price: ${recommended_price}"

        # Calculate royalties
        amazon_royalty_tier = (
            "70%" if recommended_price >= 2.99 else "35%"
        )
        amazon_royalty_amount = recommended_price * (
            0.70 if amazon_royalty_tier == "70%" else 0.35
        )
        # Note: 70% tier has delivery fee, but we'll ignore it for now (typically < $0.10)

        google_royalty_amount = recommended_price * self.GOOGLE_ROYALTY_RATE
        apple_royalty_amount = recommended_price * self.APPLE_VIA_D2D_RATE

        pricing = PricingInfo(
            base_price_usd=recommended_price,
            amazon={
                "usd": recommended_price,
                "royalty_tier": amazon_royalty_tier,
                "royalty_amount": round(amazon_royalty_amount, 2),
            },
            google={
                "usd": recommended_price,
                "royalty_amount": round(google_royalty_amount, 2),
                "note": "Google converts to local currency",
            },
            apple_via_d2d={
                "usd": recommended_price,
                "royalty_amount": round(apple_royalty_amount, 2),
                "note": "D2D handles currency conversion",
            },
            reasoning=reason,
        )

        state["pricing"] = pricing.model_dump()

        return state

    def _estimate_word_count(self, state: FlowState) -> int:
        """Estimate word count from rewritten chapters."""
        if not state.get("rewritten"):
            # Fallback: use raw text if available
            if state.get("raw_text"):
                return len(state["raw_text"].split())
            return 100000  # Default assumption

        total_words = 0
        for chapter_doc in state["rewritten"]:
            for pair in chapter_doc.get("pairs", []):
                # Use modernized text for word count
                modern_text = pair.get("modern", "")
                total_words += len(modern_text.split())

        return total_words


def calculate_pricing_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for pricing calculation."""
    optimizer = PricingOptimizer()
    state = optimizer.calculate_optimal_pricing(state)

    pricing = state["pricing"]

    print(f"\n✓ Pricing optimization complete")
    print(f"  Base price: ${pricing['base_price_usd']:.2f} USD")
    print(f"  Amazon royalty: {pricing['amazon']['royalty_tier']} (${pricing['amazon']['royalty_amount']:.2f} per sale)")
    print(f"  Google royalty: ${pricing['google']['royalty_amount']:.2f} per sale")
    print(f"  Apple (via D2D) royalty: ${pricing['apple_via_d2d']['royalty_amount']:.2f} per sale")
    print(f"  Reasoning: {pricing['reasoning']}\n")

    return {"pricing": state["pricing"]}
