import typer
from typing import Optional
from pathlib import Path
import json

from dyscount_core.config import Config

app = typer.Typer(help="Manage configuration")


@app.command()
def show(
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Show current configuration"""
    if config_file:
        # TODO: Load from file
        config = Config()
    else:
        config = Config()
    
    typer.echo(json.dumps(config.model_dump(), indent=2, default=str))


@app.command()
def validate(
    config_file: str = typer.Argument(..., help="Path to config file to validate"),
):
    """Validate a configuration file"""
    try:
        path = Path(config_file)
        if not path.exists():
            typer.echo(f"Error: Config file not found: {config_file}", err=True)
            raise typer.Exit(1)
        
        # Try to load and validate
        with open(path) as f:
            data = json.load(f)
        
        config = Config(**data)
        typer.echo("✓ Configuration is valid")
        
    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
