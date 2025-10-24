"""Edition file preparation for multi-retailer distribution.

Prepares separate EPUB files for each edition (Kindle vs Universal).
Currently creates copies with different filenames; future enhancements
could add retailer-specific metadata or formatting.
"""

import shutil
from pathlib import Path
from typing import Any

from lily_books.models import EditionInfo, FlowState


class EditionFileManager:
    """Prepares separate EPUB files for each edition if needed."""

    def prepare_edition_files(self, state: FlowState) -> FlowState:
        """
        Create edition-specific EPUB files.

        Currently: Just copy the same EPUB with different filenames
        Future: Could add retailer-specific metadata/formatting
        """
        if not state.get("epub_path"):
            raise ValueError("EPUB must be built before preparing editions")

        if not state.get("identifiers"):
            raise ValueError("Identifiers must be assigned before preparing editions")

        source_epub = Path(state["epub_path"])

        if not source_epub.exists():
            raise FileNotFoundError(f"Source EPUB not found: {source_epub}")

        # Create editions directory
        editions_dir = source_epub.parent / "editions"
        editions_dir.mkdir(exist_ok=True)

        edition_files = []

        for edition_dict in state["identifiers"]["editions"]:
            edition = EditionInfo(**edition_dict)

            suffix = edition.file_suffix
            edition_filename = source_epub.stem + suffix + source_epub.suffix
            edition_path = editions_dir / edition_filename

            # Copy EPUB
            shutil.copy2(source_epub, edition_path)

            # Update metadata in EPUB if needed (future enhancement)
            # self._update_epub_metadata(edition_path, edition_metadata)

            edition_file_info = {
                "edition_name": edition.name,
                "retailer": edition.retailer,
                "file_path": str(edition_path),
                "identifier_type": edition.identifier.identifier_type,
                "identifier_value": edition.identifier.identifier_value,
            }

            edition_files.append(edition_file_info)

            print(f"✓ Prepared {edition.name}: {edition_path.name}")

        state["edition_files"] = edition_files

        # Update edition_metadata with file paths
        if state.get("edition_metadata"):
            for i, meta in enumerate(state["edition_metadata"]):
                if i < len(edition_files):
                    meta["file_path"] = edition_files[i]["file_path"]

        return state

    def _update_epub_metadata(
        self, epub_path: Path, edition_metadata: dict
    ) -> None:
        """
        Update metadata inside EPUB for edition-specific info.

        Future enhancement: Modify OPF metadata to include edition info.
        """
        # TODO: Use ebooklib to update metadata in EPUB
        # This would allow setting different titles, publishers, etc. per edition
        pass


def prepare_editions_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for edition file preparation."""
    manager = EditionFileManager()
    state = manager.prepare_edition_files(state)

    print(
        f"✓ Prepared {len(state['edition_files'])} edition file(s) for distribution"
    )

    return {
        "edition_files": state["edition_files"],
        "edition_metadata": state.get("edition_metadata"),
    }
