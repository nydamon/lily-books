"""Free identifier management for book editions.

Manages assignment of free identifiers across different retailers:
- Amazon KDP: Free ASIN (auto-assigned at upload)
- Google Play Books: Free Google ID (auto-assigned)
- Draft2Digital: Free ISBN (from D2D's pool)
"""

from typing import Any

from lily_books.models import EditionInfo, FlowState, IdentifierInfo


class FreeIdentifierManager:
    """Manages free identifier assignment for retail distribution."""

    # Identifier assignment rules
    ASSIGNMENT_RULES = {
        "amazon_kdp": {
            "type": "ASIN",
            "cost": 0,
            "source": "amazon_auto_assign",
            "exclusive": True,  # This file can only be on Amazon
            "notes": "Generated at upload time",
        },
        "google_play": {
            "type": "GOOGLE_ID",
            "cost": 0,
            "source": "google_auto_assign",
            "exclusive": False,
            "notes": "Internal Google identifier",
        },
        "draft2digital": {
            "type": "ISBN",
            "cost": 0,
            "source": "draft2digital_free_isbn",
            "exclusive": False,
            "covers": ["apple", "kobo", "bn", "scribd", "overdrive"],
            "notes": "D2D as publisher of record",
        },
    }

    def assign_identifiers(self, state: FlowState) -> FlowState:
        """
        Assign free identifiers based on distribution targets.

        Creates two edition strategies:
        1. Amazon Kindle Edition (ASIN)
        2. Universal Edition (D2D free ISBN for Apple, etc.)
        """
        target_retailers = state.get("target_retailers", [])

        if not target_retailers:
            # Default to all free retailers
            target_retailers = ["amazon", "google", "draft2digital"]

        editions = []

        # Edition 1: Amazon Kindle
        if "amazon" in target_retailers:
            kindle_identifier = IdentifierInfo(
                identifier_type="ASIN",
                identifier_value=None,  # AUTO_ASSIGNED_AT_UPLOAD
                source="amazon_auto_assign",
                cost=0.0,
                exclusive=True,
                notes="Amazon assigns ASIN at publish time",
            )

            kindle_edition = EditionInfo(
                name="Kindle Edition",
                retailer="amazon_kdp",
                identifier=kindle_identifier,
                file_suffix="_kindle",
                file_path=None,  # Will be set by edition preparation
                exclusive_to="amazon",
                distribution_to=[],
                publisher_of_record=state.get("publishing_metadata", {}).get(
                    "publisher", "Modernized Classics Press"
                ),
            )

            editions.append(kindle_edition)

        # Edition 2: Universal (for all other retailers)
        other_retailers = [r for r in target_retailers if r != "amazon"]
        if other_retailers:
            # Determine distribution channels
            distribution_channels = []
            if "google" in other_retailers:
                distribution_channels.append("google")
            if "draft2digital" in other_retailers:
                distribution_channels.extend(
                    ["apple", "kobo", "bn", "scribd", "overdrive"]
                )

            # Use D2D free ISBN if D2D is in the list, otherwise Google ID
            if "draft2digital" in other_retailers:
                universal_identifier = IdentifierInfo(
                    identifier_type="ISBN",
                    identifier_value=None,  # AUTO_ASSIGNED_BY_D2D
                    source="draft2digital_free_isbn",
                    cost=0.0,
                    exclusive=False,
                    notes="D2D assigns free ISBN at upload",
                )
                retailer = "draft2digital"
                publisher_of_record = "Draft2Digital, LLC"
            else:
                # Google only
                universal_identifier = IdentifierInfo(
                    identifier_type="GOOGLE_ID",
                    identifier_value=None,  # AUTO_ASSIGNED_BY_GOOGLE
                    source="google_auto_assign",
                    cost=0.0,
                    exclusive=False,
                    notes="Google assigns ID at upload",
                )
                retailer = "google_play"
                publisher_of_record = state.get("publishing_metadata", {}).get(
                    "publisher", "Modernized Classics Press"
                )

            universal_edition = EditionInfo(
                name="Universal Edition",
                retailer=retailer,
                identifier=universal_identifier,
                file_suffix="_universal",
                file_path=None,
                exclusive_to=None,
                distribution_to=distribution_channels,
                publisher_of_record=publisher_of_record,
            )

            editions.append(universal_edition)

        # Update state
        identifiers = {"editions": [e.model_dump() for e in editions]}

        state["identifiers"] = identifiers
        state["requires_two_editions"] = len(editions) > 1

        return state

    def generate_edition_metadata(self, state: FlowState) -> FlowState:
        """
        Generate edition-specific metadata.

        Amazon and D2D need slightly different titles to differentiate editions.
        """
        if not state.get("identifiers"):
            raise ValueError("Identifiers must be assigned first")

        base_title = state.get("publishing_metadata", {}).get("title", "Untitled")
        subtitle = state.get("publishing_metadata", {}).get("subtitle", "")
        description = state.get("retail_metadata", {}).get("description_long", "")
        keywords = state.get("retail_metadata", {}).get("keywords", [])
        categories = state.get("retail_metadata", {}).get("bisac_categories", [])

        edition_metadata = []

        for edition_dict in state["identifiers"]["editions"]:
            # Reconstruct EditionInfo from dict
            edition = EditionInfo(**edition_dict)

            edition_meta = {
                "edition_name": edition.name,
                "retailer": edition.retailer,
                "title": base_title,
                "subtitle": subtitle,
                "description": description,
                "keywords": keywords,
                "categories": categories,
                "file_path": None,  # Will be set by file preparation node
                "notes": "",
            }

            # Amazon-specific adjustments
            if edition.retailer == "amazon_kdp":
                # No suffix needed on Amazon
                edition_meta["notes"] = "Exclusive Kindle edition"

            # D2D-specific adjustments
            elif edition.retailer == "draft2digital":
                edition_meta[
                    "notes"
                ] = "Available on Apple Books, Google Play, Kobo, and more"

            # Google-specific adjustments
            elif edition.retailer == "google_play":
                edition_meta["notes"] = "Available on Google Play Books"

            edition_metadata.append(edition_meta)

        state["edition_metadata"] = edition_metadata

        return state


def assign_identifiers_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for identifier assignment."""
    manager = FreeIdentifierManager()
    state = manager.assign_identifiers(state)
    state = manager.generate_edition_metadata(state)

    print(
        f"✓ Assigned identifiers for {len(state['identifiers']['editions'])} edition(s)"
    )
    for edition_dict in state["identifiers"]["editions"]:
        edition = EditionInfo(**edition_dict)
        print(
            f"  - {edition.name}: {edition.identifier.identifier_type} via {edition.retailer}"
        )

    return {
        "identifiers": state["identifiers"],
        "requires_two_editions": state["requires_two_editions"],
        "edition_metadata": state["edition_metadata"],
    }
