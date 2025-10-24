"""FastAPI application for book modernization pipeline."""

from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import ensure_directories
from ..models import ParaPair
from ..storage import (
    append_log_entry,
    load_chapter_doc,
    load_state,
    save_chapter_doc,
    save_state,
)


# Request/Response models
class ProjectCreateRequest(BaseModel):
    book_id: int
    slug: str


class ProjectCreateResponse(BaseModel):
    slug: str
    book_id: int
    status: str


class ChapterPairsResponse(BaseModel):
    chapter: int
    title: str
    pairs: list[ParaPair]


class PairUpdateRequest(BaseModel):
    modern: str
    notes: str | None = None


class QASummaryResponse(BaseModel):
    total_chapters: int
    passed_chapters: int
    total_issues: int
    fidelity_scores: list[int]
    readability_grades: list[float]


class HealthResponse(BaseModel):
    status: str
    api_keys_configured: bool
    models_available: bool


# Initialize FastAPI app
app = FastAPI(
    title="Lily Books API",
    description="LangChain/LangGraph pipeline for public-domain book modernization",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/projects", response_model=ProjectCreateResponse)
async def create_project(request: ProjectCreateRequest) -> ProjectCreateResponse:
    """Create a new project."""
    try:
        # Ensure directories exist
        ensure_directories(request.slug)

        # Initialize state
        initial_state = {
            "slug": request.slug,
            "book_id": request.book_id,
            "paths": {},
            "chapters": None,
            "rewritten": None,
            "qa_text_ok": None,
            "audio_ok": None,
            "errors": [],
        }

        # Save initial state
        save_state(request.slug, initial_state)

        # Log project creation
        append_log_entry(
            request.slug,
            {
                "action": "project_created",
                "book_id": request.book_id,
                "status": "created",
            },
        )

        return ProjectCreateResponse(
            slug=request.slug, book_id=request.book_id, status="created"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@app.get("/api/projects/{slug}/status")
async def get_project_status(slug: str) -> dict[str, Any]:
    """Get project status and state."""
    state = load_state(slug)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {slug} not found"
        )

    return state


@app.get(
    "/api/projects/{slug}/chapters/{chapter_num}/pairs",
    response_model=ChapterPairsResponse,
)
async def get_chapter_pairs(slug: str, chapter_num: int) -> ChapterPairsResponse:
    """Get paragraph pairs for a specific chapter."""
    chapter_doc = load_chapter_doc(slug, chapter_num)
    if not chapter_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_num} not found for project {slug}",
        )

    return ChapterPairsResponse(
        chapter=chapter_doc.chapter, title=chapter_doc.title, pairs=chapter_doc.pairs
    )


@app.patch("/api/projects/{slug}/chapters/{chapter_num}/pairs/{pair_index}")
async def update_pair(
    slug: str, chapter_num: int, pair_index: int, request: PairUpdateRequest
) -> dict[str, str]:
    """Update modern text for a specific paragraph pair (HITL edit)."""
    chapter_doc = load_chapter_doc(slug, chapter_num)
    if not chapter_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_num} not found for project {slug}",
        )

    if pair_index >= len(chapter_doc.pairs):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pair index {pair_index} out of range",
        )

    # Update the pair
    chapter_doc.pairs[pair_index].modern = request.modern
    if request.notes:
        chapter_doc.pairs[pair_index].notes = request.notes

    # Save updated chapter
    save_chapter_doc(slug, chapter_num, chapter_doc)

    # Log the edit
    append_log_entry(
        slug,
        {
            "action": "pair_updated",
            "chapter": chapter_num,
            "pair_index": pair_index,
            "notes": request.notes,
        },
    )

    return {"status": "updated"}


@app.post("/api/projects/{slug}/chapters/{chapter_num}/retry")
async def retry_chapter(slug: str, chapter_num: int) -> dict[str, str]:
    """Trigger remediation for a specific chapter."""
    # TODO: Implement remediation logic
    append_log_entry(
        slug, {"action": "chapter_retry_requested", "chapter": chapter_num}
    )

    return {"status": "retry_requested"}


@app.get("/api/projects/{slug}/qa/summary", response_model=QASummaryResponse)
async def get_qa_summary(slug: str) -> QASummaryResponse:
    """Get aggregated QA metrics across all chapters."""
    state = load_state(slug)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {slug} not found"
        )

    if not state.get("rewritten"):
        return QASummaryResponse(
            total_chapters=0,
            passed_chapters=0,
            total_issues=0,
            fidelity_scores=[],
            readability_grades=[],
        )

    total_chapters = len(state["rewritten"])
    passed_chapters = 0
    total_issues = 0
    fidelity_scores = []
    readability_grades = []

    for chapter_doc in state["rewritten"]:
        chapter_num = chapter_doc.chapter
        chapter_doc = load_chapter_doc(slug, chapter_num)

        if chapter_doc and chapter_doc.pairs:
            chapter_passed = True
            for pair in chapter_doc.pairs:
                if pair.qa:
                    fidelity_scores.append(pair.qa.fidelity_score)
                    readability_grades.append(pair.qa.readability_grade)
                    total_issues += len(pair.qa.issues)

                    if not (
                        pair.qa.modernization_complete and pair.qa.formatting_preserved
                    ):
                        chapter_passed = False

            if chapter_passed:
                passed_chapters += 1

    return QASummaryResponse(
        total_chapters=total_chapters,
        passed_chapters=passed_chapters,
        total_issues=total_issues,
        fidelity_scores=fidelity_scores,
        readability_grades=readability_grades,
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health and configuration."""
    from ..config import settings

    # Check API keys (respect optional features)
    api_keys_ok = bool(settings.openrouter_api_key)

    if settings.enable_audio:
        api_keys_ok = api_keys_ok and bool(settings.fish_api_key)

    api_keys_ok = api_keys_ok and bool(settings.ideogram_api_key)

    if settings.langfuse_enabled:
        api_keys_ok = api_keys_ok and bool(
            settings.langfuse_public_key and settings.langfuse_secret_key
        )

    # TODO: Add model connectivity checks
    models_ok = True

    return HealthResponse(
        status="healthy" if api_keys_ok and models_ok else "degraded",
        api_keys_configured=api_keys_ok,
        models_available=models_ok,
    )


@app.get("/api/costs/{slug}")
async def get_costs(slug: str) -> dict[str, Any]:
    """Get token usage and cost summary from logs."""
    # TODO: Implement cost tracking from logs
    return {"slug": slug, "total_tokens": 0, "estimated_cost": 0.0, "breakdown": {}}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
