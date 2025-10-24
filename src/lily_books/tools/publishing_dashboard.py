"""Publishing dashboard for monitoring distribution pipeline.

Simple file-based dashboard for tracking publishing status across books.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from lily_books.models import FlowState


class PublishingDashboard:
    """Simple file-based dashboard for monitoring publishing pipeline."""

    def __init__(self, dashboard_dir: str = "dashboard"):
        self.dashboard_dir = Path(dashboard_dir)
        self.dashboard_dir.mkdir(exist_ok=True)

        self.status_file = self.dashboard_dir / "status.json"
        self.log_file = self.dashboard_dir / "publishing_log.jsonl"

    def log_book_status(self, state: FlowState) -> None:
        """Log book publishing status."""

        entry = {
            "timestamp": datetime.now().isoformat(),
            "slug": state.get("slug", "unknown"),
            "title": state.get("publishing_metadata", {}).get("title", "Unknown"),
            "author": state.get("publishing_metadata", {}).get("original_author", "Unknown"),
            "identifiers": state.get("identifiers", {}),
            "upload_status": state.get("upload_status", {}),
            "upload_results": state.get("upload_results", {}),
            "errors": state.get("errors", []),
            "pricing": state.get("pricing", {}),
            "metadata_validated": state.get("metadata_validated", False),
            "epub_validated": state.get("epub_validated", False),
            "human_approved": state.get("human_approved", False),
        }

        # Append to log
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Update status file
        self._update_status_file(entry)

    def _update_status_file(self, entry: dict) -> None:
        """Update aggregate status file."""

        if self.status_file.exists():
            with open(self.status_file) as f:
                status = json.load(f)
        else:
            status = {"books": []}

        # Find existing entry or append new
        existing = next(
            (b for b in status["books"] if b["slug"] == entry["slug"]),
            None,
        )

        if existing:
            existing.update(entry)
        else:
            status["books"].append(entry)

        with open(self.status_file, "w") as f:
            json.dump(status, f, indent=2)

    def generate_report(self) -> str:
        """Generate human-readable status report."""

        if not self.status_file.exists():
            return "No books published yet."

        with open(self.status_file) as f:
            status = json.load(f)

        report = "\n"
        report += "PUBLISHING DASHBOARD\n"
        report += "=" * 70 + "\n\n"

        for book in status["books"]:
            report += f"Title: {book['title']}\n"
            report += f"Author: {book['author']}\n"
            report += f"Slug: {book['slug']}\n"
            report += f"Last Updated: {book['timestamp']}\n"

            # Upload status
            upload_status = book.get("upload_status", {})
            if upload_status:
                report += "\nUpload Status:\n"
                for retailer, stat in upload_status.items():
                    icon = "✓" if stat == "success" else "⏳" if stat == "pending" else "✗"
                    report += f"  {icon} {retailer.upper()}: {stat}\n"

            # Identifiers
            identifiers = book.get("identifiers", {})
            if identifiers and identifiers.get("editions"):
                report += "\nIdentifiers:\n"
                for edition in identifiers["editions"]:
                    identifier = edition.get("identifier", {})
                    report += f"  - {edition['name']}: {identifier.get('identifier_type', 'N/A')}\n"

            # Pricing
            pricing = book.get("pricing", {})
            if pricing:
                report += f"\nPricing: ${pricing.get('base_price_usd', 0.00):.2f} USD\n"

            # Errors
            errors = book.get("errors", [])
            if errors:
                report += "\nErrors:\n"
                for error in errors:
                    report += f"  - {error}\n"

            report += "\n" + "-" * 70 + "\n\n"

        return report


def generate_publishing_report_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for generating publishing report."""

    dashboard = PublishingDashboard()
    dashboard.log_book_status(state)

    print("\n" + "=" * 70)
    print("PUBLISHING COMPLETE".center(70))
    print("=" * 70)
    print(dashboard.generate_report())

    return {}
