import typer
import uvicorn

import template.lib

app = typer.Typer(
    name=template.lib.TEMPLATE,
    no_args_is_help=True,
    rich_help_panel="template",
    rich_markup_mode="rich",
)


@app.command()
def hello(name: str):
    print(f"I am {template.lib.TEMPLATE}, I was given {name}!")


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
