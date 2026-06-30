"""graph2obsidian CLI."""

from pathlib import Path

import typer
from rich.console import Console

import graph2obsidian
from graph2obsidian.converter import convert
from graph2obsidian.parser import load_graph

app = typer.Typer(
    name="graph2obsidian",
    no_args_is_help=True,
    rich_help_panel="graph2obsidian",
    rich_markup_mode="rich",
)

console = Console()


@app.command()
def convert_cmd(
    input: Path = typer.Argument(..., help="Path to the graph JSON file."),
    output: Path = typer.Option(Path("vault"), "--output", "-o", help="Directory to write Obsidian notes into."),
) -> None:
    """Convert a graph JSON file into an Obsidian vault."""
    if not input.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input}")
        raise typer.Exit(code=1)

    graph = load_graph(input)
    written = convert(graph, output)

    console.print(f"[green]✓[/green] Wrote {len(written)} note(s) to [bold]{output}[/bold]")
    for path in written:
        console.print(f"  {path}")


@app.command()
def version() -> None:
    """Print the version."""
    console.print(graph2obsidian.__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
