import typer
from typing import Optional

from .commands import serve, config

app = typer.Typer(
    name="dyscount",
    help="Dyscount - DynamoDB-compatible API service",
    no_args_is_help=True,
)

app.add_typer(serve.app, name="serve")
app.add_typer(config.app, name="config")


def version_callback(value: bool):
    if value:
        from dyscount_cli import __version__
        typer.echo(f"Dyscount CLI v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit."
    ),
):
    """Dyscount CLI - DynamoDB-compatible API service"""
    pass


if __name__ == "__main__":
    app()
