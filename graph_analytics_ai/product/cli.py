"""CLI entry points for the optional product API server."""

import click

from .fastapi_app import create_product_fastapi_app


@click.group()
def cli() -> None:
    """Agentic Graph Analytics product UI commands."""


@cli.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
@click.option("--reload", is_flag=True, help="Enable server reload during development.")
@click.option(
    "--log-level",
    default="info",
    show_default=True,
    help="Uvicorn log level.",
)
def serve(host: str, port: int, reload: bool, log_level: str) -> None:
    """Run the product API server."""

    try:
        import uvicorn
    except ImportError as exc:
        raise click.ClickException(
            "Product API serving requires the optional api extra: "
            "pip install 'graph-analytics-ai[api]'"
        ) from exc

    app = create_product_fastapi_app()
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


def main() -> None:
    """Run the product API CLI."""

    cli()


if __name__ == "__main__":
    main()
