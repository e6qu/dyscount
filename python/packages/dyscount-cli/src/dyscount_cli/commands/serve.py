import typer
from typing import Optional
import uvicorn

from dyscount_api.main import create_app
from dyscount_core.config import Config

app = typer.Typer(help="Run the Dyscount server")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Start the Dyscount server"""
    # Load config
    if config_file:
        # TODO: Load from file
        config = Config()
    else:
        config = Config()
    
    # Create app
    app = create_app(config)
    
    typer.echo(f"Starting Dyscount server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
