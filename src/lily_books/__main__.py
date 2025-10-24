"""CLI entry point for Lily Books."""


import typer

from .api.main import app
from .runner import get_pipeline_status, run_pipeline
from .utils.ssl_fix import fix_ssl_certificates

# Fix SSL certificates on startup
fix_ssl_certificates()

cli = typer.Typer()


@cli.command()
def run(
    book_id: int = typer.Argument(..., help="Gutendex book ID"),
    slug: str = typer.Option(..., "--slug", "-s", help="Project slug identifier"),
    chapters: str
    | None = typer.Option(
        None, "--chapters", "-c", help="Comma-separated chapter numbers"
    ),
):
    """Run the complete book modernization pipeline."""
    chapter_list = None
    if chapters:
        chapter_list = [int(x.strip()) for x in chapters.split(",")]

    result = run_pipeline(slug, book_id, chapter_list)

    if result["success"]:
        typer.echo(f"✅ Pipeline completed successfully for {slug}")
        typer.echo(f"📚 Book ID: {book_id}")
        typer.echo(f"⏱️  Runtime: {result['runtime_sec']:.1f} seconds")
        typer.echo(f"📖 EPUB: {result['deliverables']['epub_path']}")
        typer.echo(f"🎵 Audio chapters: {result['deliverables']['audio_chapters']}")
    else:
        typer.echo(f"❌ Pipeline failed for {slug}")
        typer.echo(f"⏱️  Runtime: {result['runtime_sec']:.1f} seconds")
        if "error" in result:
            typer.echo(f"   • {result['error']}")
        if "errors" in result:
            for error in result["errors"]:
                typer.echo(f"   • {error}")


@cli.command()
def status(slug: str = typer.Argument(..., help="Project slug identifier")):
    """Get pipeline status and progress."""
    status_info = get_pipeline_status(slug)

    if status_info["status"] == "not_found":
        typer.echo(f"❌ Project {slug} not found")
        return

    typer.echo(f"📊 Status for {slug}")
    typer.echo(
        f"📈 Progress: {status_info['completed_steps']}/{status_info['total_steps']} steps"
    )

    for step, completed in status_info["progress"].items():
        status_icon = "✅" if completed else "⏳"
        typer.echo(f"   {status_icon} {step}")


@cli.command()
def api(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the FastAPI server."""
    import uvicorn

    typer.echo("🚀 Starting Lily Books API server")
    typer.echo(f"🌐 http://{host}:{port}")
    typer.echo(f"📚 Docs: http://{host}:{port}/docs")

    uvicorn.run(app, host=host, port=port, reload=reload)


if __name__ == "__main__":
    cli()
