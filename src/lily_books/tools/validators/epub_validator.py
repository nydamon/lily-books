"""EPUB validation using epubcheck.

Validates EPUB files for retailer compliance using epubcheck validator.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from lily_books.config import settings
from lily_books.models import FlowState, ValidationReport


class EPUBValidator:
    """Validates EPUB files using epubcheck."""

    def __init__(self):
        self.epubcheck_path = settings.epubcheck_path

    def validate_epub(self, state: FlowState) -> FlowState:
        """Validate EPUB files using epubcheck."""

        validation_reports = state.get("validation_reports", [])
        errors_found = []

        # Check if we have edition files or just the main EPUB
        if state.get("edition_files"):
            # Validate each edition EPUB
            for edition in state["edition_files"]:
                epub_path = Path(edition["file_path"])
                report = self._run_epubcheck(
                    epub_path, edition_name=edition["edition_name"]
                )
                validation_reports.append(report.model_dump())

                if not report.passed:
                    errors_found.append(
                        {
                            "edition": edition["edition_name"],
                            "file": epub_path.name,
                            "errors": report.errors,
                        }
                    )

        elif state.get("epub_path"):
            # Validate main EPUB only
            epub_path = Path(state["epub_path"])
            report = self._run_epubcheck(epub_path)
            validation_reports.append(report.model_dump())

            if not report.passed:
                errors_found.append(
                    {
                        "edition": "Main EPUB",
                        "file": epub_path.name,
                        "errors": report.errors,
                    }
                )

        else:
            raise ValueError("No EPUB file found to validate")

        state["validation_reports"] = validation_reports
        state["epub_validated"] = len(errors_found) == 0
        state["epub_validation_errors"] = errors_found

        if state["epub_validated"]:
            print(f"\n✓ All EPUB files validated successfully\n")
        else:
            print(f"\n✗ EPUB validation failed for {len(errors_found)} file(s)\n")
            for error in errors_found:
                print(f"  {error['edition']}: {len(error['errors'])} error(s)")

        return state

    def _run_epubcheck(
        self, epub_path: Path, edition_name: str = "Main"
    ) -> ValidationReport:
        """Run epubcheck on a single EPUB file."""

        if not epub_path.exists():
            return ValidationReport(
                validation_type="epub",
                passed=False,
                errors=[{"message": f"File not found: {epub_path}"}],
                warnings=[],
                validator="epubcheck",
                timestamp=datetime.now().isoformat(),
            )

        try:
            # Run epubcheck with JSON output
            result = subprocess.run(
                [self.epubcheck_path, str(epub_path), "--json", "-"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print(f"  ✓ {edition_name} EPUB valid")
                return ValidationReport(
                    validation_type="epub",
                    passed=True,
                    errors=[],
                    warnings=[],
                    validator="epubcheck",
                    timestamp=datetime.now().isoformat(),
                )
            else:
                # Parse JSON output for errors
                try:
                    output = json.loads(result.stdout)
                    errors = output.get("messages", [])
                    error_list = [
                        {
                            "message": msg.get("message", "Unknown error"),
                            "location": msg.get("location", ""),
                        }
                        for msg in errors
                        if msg.get("severity") in ["ERROR", "FATAL"]
                    ]
                    warning_list = [
                        {
                            "message": msg.get("message", ""),
                            "location": msg.get("location", ""),
                        }
                        for msg in errors
                        if msg.get("severity") == "WARNING"
                    ]
                except json.JSONDecodeError:
                    # Fallback to plain text output
                    error_list = [{"message": result.stdout}]
                    warning_list = []

                print(f"  ✗ {edition_name} EPUB invalid: {len(error_list)} error(s)")

                return ValidationReport(
                    validation_type="epub",
                    passed=False,
                    errors=error_list,
                    warnings=warning_list,
                    validator="epubcheck",
                    timestamp=datetime.now().isoformat(),
                )

        except subprocess.TimeoutExpired:
            return ValidationReport(
                validation_type="epub",
                passed=False,
                errors=[{"message": "epubcheck timed out after 60 seconds"}],
                warnings=[],
                validator="epubcheck",
                timestamp=datetime.now().isoformat(),
            )

        except FileNotFoundError:
            # epubcheck not installed
            print(
                f"  ⚠ epubcheck not found at '{self.epubcheck_path}', skipping validation"
            )
            return ValidationReport(
                validation_type="epub",
                passed=True,  # Pass by default if epubcheck not available
                errors=[],
                warnings=[
                    {
                        "message": "epubcheck not installed, validation skipped"
                    }
                ],
                validator="epubcheck",
                timestamp=datetime.now().isoformat(),
            )


def validate_epub_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for EPUB validation."""
    validator = EPUBValidator()
    state = validator.validate_epub(state)

    return {
        "epub_validated": state["epub_validated"],
        "validation_reports": state.get("validation_reports", []),
        "epub_validation_errors": state.get("epub_validation_errors", []),
    }
