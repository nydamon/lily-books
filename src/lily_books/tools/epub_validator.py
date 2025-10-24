"""EPUB validation and quality assessment tools."""

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


@dataclass
class EPUBValidationResult:
    """Result of EPUB validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    quality_score: int
    suggestions: list[str]


def validate_epub_structure(epub_path: Path) -> EPUBValidationResult:
    """Validate EPUB structure and content quality."""
    errors = []
    warnings = []
    suggestions = []

    try:
        with zipfile.ZipFile(epub_path, "r") as epub:
            # Check required files
            required_files = ["mimetype", "META-INF/container.xml", "EPUB/content.opf"]

            for req_file in required_files:
                if req_file not in [f.filename for f in epub.filelist]:
                    errors.append(f"Missing required file: {req_file}")

            # Check content files
            content_files = [f for f in epub.filelist if f.filename.endswith(".xhtml")]
            if len(content_files) < 2:
                errors.append(
                    "EPUB should have at least 2 content files (cover + chapters)"
                )

            # Analyze content quality
            total_content_length = 0
            chapter_count = 0
            illustration_placeholders = 0

            for file_info in content_files:
                if "chapter" in file_info.filename:
                    chapter_count += 1
                    content = epub.read(file_info.filename).decode("utf-8")
                    total_content_length += len(content)

                    # Check for illustration placeholders
                    if "[Illustration]" in content:
                        illustration_placeholders += 1
                        warnings.append(
                            f"Chapter {file_info.filename} contains [Illustration] placeholder"
                        )

            # Content quality checks
            if total_content_length < 1000:
                warnings.append("EPUB has very little content")
                suggestions.append("Add more content to chapters")

            if illustration_placeholders > 0:
                suggestions.append(
                    "Replace [Illustration] placeholders with actual content or remove them"
                )

            # Check for CSS styling
            css_files = [f for f in epub.filelist if f.filename.endswith(".css")]
            if not css_files:
                warnings.append("No CSS styling found")
                suggestions.append("Add CSS styling for better appearance")

            # Calculate quality score
            quality_score = 100
            quality_score -= len(errors) * 20
            quality_score -= len(warnings) * 10
            quality_score -= illustration_placeholders * 15

            if total_content_length < 1000:
                quality_score -= 20

            if not css_files:
                quality_score -= 25

            quality_score = max(0, quality_score)

            return EPUBValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                quality_score=quality_score,
                suggestions=suggestions,
            )

    except Exception as e:
        return EPUBValidationResult(
            valid=False,
            errors=[f"Failed to validate EPUB: {str(e)}"],
            warnings=[],
            quality_score=0,
            suggestions=[],
        )


def analyze_epub_content(epub_path: Path) -> dict[str, Any]:
    """Analyze EPUB content for quality assessment."""
    try:
        with zipfile.ZipFile(epub_path, "r") as epub:
            analysis = {
                "total_files": len(epub.filelist),
                "content_files": 0,
                "css_files": 0,
                "total_content_length": 0,
                "chapter_count": 0,
                "illustration_placeholders": 0,
                "has_cover": False,
                "has_toc": False,
            }

            for file_info in epub.filelist:
                if file_info.filename.endswith(".xhtml"):
                    analysis["content_files"] += 1
                    content = epub.read(file_info.filename).decode("utf-8")
                    analysis["total_content_length"] += len(content)

                    if "cover" in file_info.filename:
                        analysis["has_cover"] = True
                    elif "chapter" in file_info.filename:
                        analysis["chapter_count"] += 1
                        if "[Illustration]" in content:
                            analysis["illustration_placeholders"] += 1

                elif file_info.filename.endswith(".css"):
                    analysis["css_files"] += 1

                elif "toc" in file_info.filename or "nav" in file_info.filename:
                    analysis["has_toc"] = True

            return analysis

    except Exception as e:
        return {"error": str(e)}


@tool
def validate_epub_tool(epub_path: str) -> str:
    """Validate EPUB file structure and content quality.

    Args:
        epub_path: Path to EPUB file to validate

    Returns:
        JSON string with validation results
    """
    import json

    result = validate_epub_structure(Path(epub_path))
    analysis = analyze_epub_content(Path(epub_path))

    return json.dumps(
        {
            "validation": {
                "valid": result.valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "quality_score": result.quality_score,
                "suggestions": result.suggestions,
            },
            "analysis": analysis,
        }
    )


def get_epub_quality_report(epub_path: Path) -> str:
    """Generate a human-readable quality report for an EPUB."""
    result = validate_epub_structure(epub_path)
    analysis = analyze_epub_content(epub_path)

    report = f"""
EPUB Quality Report: {epub_path.name}
{'=' * 50}

VALIDATION STATUS: {'✅ VALID' if result.valid else '❌ INVALID'}

Quality Score: {result.quality_score}/100

CONTENT ANALYSIS:
• Total files: {analysis.get('total_files', 0)}
• Content files: {analysis.get('content_files', 0)}
• CSS files: {analysis.get('css_files', 0)}
• Chapters: {analysis.get('chapter_count', 0)}
• Total content length: {analysis.get('total_content_length', 0)} characters
• Illustration placeholders: {analysis.get('illustration_placeholders', 0)}
• Has cover: {'✅' if analysis.get('has_cover') else '❌'}
• Has table of contents: {'✅' if analysis.get('has_toc') else '❌'}

"""

    if result.errors:
        report += "ERRORS:\n"
        for error in result.errors:
            report += f"❌ {error}\n"
        report += "\n"

    if result.warnings:
        report += "WARNINGS:\n"
        for warning in result.warnings:
            report += f"⚠️ {warning}\n"
        report += "\n"

    if result.suggestions:
        report += "SUGGESTIONS FOR IMPROVEMENT:\n"
        for suggestion in result.suggestions:
            report += f"💡 {suggestion}\n"
        report += "\n"

    return report
