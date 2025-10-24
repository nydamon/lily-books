"""Metadata validation for retail distribution.

Validates that metadata meets retailer requirements for:
- Amazon KDP
- Google Play Books
- Apple Books (via Draft2Digital)
"""

from datetime import datetime
from typing import Any

from lily_books.models import FlowState, PublishingMetadata, ValidationReport


class MetadataValidator:
    """Validates metadata for retailer compliance."""

    # Retailer requirements
    REQUIREMENTS = {
        "amazon": {
            "title_max": 200,
            "subtitle_max": 200,
            "description_max": 4000,
            "keywords_max": 7,
            "categories_max": 2,
        },
        "google": {
            "title_max": 255,
            "description_min": 200,
            "description_max": 4000,
        },
        "apple": {
            "title_max": 255,
            "description_max": 4000,
        },
    }

    def validate_metadata(self, state: FlowState) -> FlowState:
        """Validate metadata for all target retailers."""

        errors = []
        warnings = []

        # Check retail metadata exists
        retail_meta = state.get("retail_metadata")
        pub_meta = state.get("publishing_metadata")
        if isinstance(pub_meta, PublishingMetadata):
            pub_meta_dict = pub_meta.model_dump()
        else:
            pub_meta_dict = pub_meta or {}

        if not retail_meta:
            errors.append({"message": "Missing retail_metadata"})
            state["metadata_validated"] = False
            return state

        if not pub_meta_dict:
            errors.append({"message": "Missing publishing_metadata"})
            state["metadata_validated"] = False
            return state

        # Get target retailers
        target_retailers = state.get("target_retailers", ["amazon", "google", "draft2digital"])

        # Validate for Amazon
        if "amazon" in target_retailers:
            amazon_errors = self._validate_amazon(retail_meta, pub_meta_dict)
            errors.extend(amazon_errors)

        # Validate for Google
        if "google" in target_retailers:
            google_errors = self._validate_google(retail_meta, pub_meta_dict)
            errors.extend(google_errors)

        # Validate for Apple (via D2D)
        if "draft2digital" in target_retailers:
            apple_errors = self._validate_apple(retail_meta, pub_meta_dict)
            errors.extend(apple_errors)

        # Create validation report
        report = ValidationReport(
            validation_type="metadata",
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validator="manual",
            timestamp=datetime.now().isoformat(),
        )

        # Update state
        validation_reports = state.get("validation_reports", [])
        validation_reports.append(report.model_dump())
        state["validation_reports"] = validation_reports
        state["metadata_validated"] = report.passed

        if report.passed:
            print(f"\n✓ Metadata validation passed\n")
        else:
            print(f"\n✗ Metadata validation failed: {len(errors)} error(s)\n")
            for error in errors:
                print(f"  - {error['message']}")

        return state

    def _validate_amazon(self, retail_meta: dict, pub_meta: dict) -> list[dict]:
        """Validate metadata for Amazon KDP."""
        errors = []
        reqs = self.REQUIREMENTS["amazon"]

        # Title length
        title = pub_meta.get("title", "")
        if len(title) > reqs["title_max"]:
            errors.append({
                "retailer": "amazon",
                "field": "title",
                "message": f"Title too long: {len(title)} chars (max {reqs['title_max']})"
            })

        # Subtitle length
        subtitle = pub_meta.get("subtitle", "")
        if subtitle and len(subtitle) > reqs["subtitle_max"]:
            errors.append({
                "retailer": "amazon",
                "field": "subtitle",
                "message": f"Subtitle too long: {len(subtitle)} chars (max {reqs['subtitle_max']})"
            })

        # Description length
        description = retail_meta.get("description_long", "")
        if len(description) > reqs["description_max"]:
            errors.append({
                "retailer": "amazon",
                "field": "description",
                "message": f"Description too long: {len(description)} chars (max {reqs['description_max']})"
            })

        # Amazon keywords
        amazon_keywords = retail_meta.get("amazon_keywords", [])
        if len(amazon_keywords) > reqs["keywords_max"]:
            errors.append({
                "retailer": "amazon",
                "field": "keywords",
                "message": f"Too many keywords: {len(amazon_keywords)} (max {reqs['keywords_max']})"
            })

        # BISAC categories
        categories = retail_meta.get("bisac_categories", [])
        if len(categories) > reqs["categories_max"]:
            errors.append({
                "retailer": "amazon",
                "field": "categories",
                "message": f"Too many categories: {len(categories)} (max {reqs['categories_max']})"
            })

        return errors

    def _validate_google(self, retail_meta: dict, pub_meta: dict) -> list[dict]:
        """Validate metadata for Google Play Books."""
        errors = []
        reqs = self.REQUIREMENTS["google"]

        # Title length
        title = pub_meta.get("title", "")
        if len(title) > reqs["title_max"]:
            errors.append({
                "retailer": "google",
                "field": "title",
                "message": f"Title too long: {len(title)} chars (max {reqs['title_max']})"
            })

        # Description length
        description = retail_meta.get("description_long", "")
        if len(description) < reqs["description_min"]:
            errors.append({
                "retailer": "google",
                "field": "description",
                "message": f"Description too short: {len(description)} chars (min {reqs['description_min']})"
            })
        if len(description) > reqs["description_max"]:
            errors.append({
                "retailer": "google",
                "field": "description",
                "message": f"Description too long: {len(description)} chars (max {reqs['description_max']})"
            })

        return errors

    def _validate_apple(self, retail_meta: dict, pub_meta: dict) -> list[dict]:
        """Validate metadata for Apple Books (via D2D)."""
        errors = []
        reqs = self.REQUIREMENTS["apple"]

        # Title length
        title = pub_meta.get("title", "")
        if len(title) > reqs["title_max"]:
            errors.append({
                "retailer": "apple",
                "field": "title",
                "message": f"Title too long: {len(title)} chars (max {reqs['title_max']})"
            })

        # Description length
        description = retail_meta.get("description_long", "")
        if len(description) > reqs["description_max"]:
            errors.append({
                "retailer": "apple",
                "field": "description",
                "message": f"Description too long: {len(description)} chars (max {reqs['description_max']})"
            })

        return errors


def validate_metadata_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for metadata validation."""
    validator = MetadataValidator()
    state = validator.validate_metadata(state)

    return {
        "metadata_validated": state["metadata_validated"],
        "validation_reports": state.get("validation_reports", []),
    }
