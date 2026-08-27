import json
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from autoreview.classifier import classify_content
from autoreview.ast_reducer import reduce_python_code
from autoreview.reviewer import run_code_review, OllamaConnectionError, ReviewError
from autoreview.render import render_rich_output

app = typer.Typer(name="autoreview", help="AutoReview-AI: Developer-centric code auditing CLI tool")
console = Console()
err_console = Console(stderr=True)

@app.callback()
def main():
    """
    AutoReview-AI: Developer-centric code auditing CLI tool.
    """
    pass

@app.command()
def review(
    path: Path = typer.Argument(
        ...,
        help="Path to the local source file or git diff to audit."
    ),
    mode: Optional[str] = typer.Option(
        None,
        "--mode",
        "-m",
        help="Override automatic submission classification. Must be one of: dsa_problem, pr_diff, snippet"
    ),
    question: Optional[str] = typer.Option(
        None,
        "--question",
        "-q",
        help="Optional question or specific context for the LLM auditor."
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Dump raw structured JSON output to stdout (useful for CI/CD)."
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Ollama model name (overrides environment variable default)."
    ),
):
    """
    Audit a local code file or git diff and return structured feedback.
    """
    # 1. Read file
    if not path.exists():
        err_console.print(f"[bold red]Error:[/bold red] File not found at path: {path}")
        raise typer.Exit(code=1)
        
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        err_console.print(f"[bold red]Error:[/bold red] Failed to read file {path}: {e}")
        raise typer.Exit(code=1)

    # 2. Determine mode
    submission_type = mode
    if submission_type:
        valid_modes = ["dsa_problem", "pr_diff", "snippet"]
        if submission_type not in valid_modes:
            err_console.print(
                f"[bold red]Error:[/bold red] Invalid mode '{submission_type}'. "
                f"Must be one of {valid_modes}"
            )
            raise typer.Exit(code=1)
    else:
        submission_type = classify_content(content, path.name)

    # 3. Context AST Reduction (only for python code under dsa_problem or snippet)
    final_content = content
    if submission_type in ("dsa_problem", "snippet") and path.suffix.lower() == ".py":
        try:
            reduced, orig_chars, red_chars = reduce_python_code(content)
            savings_pct = (1 - (red_chars / orig_chars)) * 100 if orig_chars > 0 else 0
            
            # Print savings to stderr so stdout remains clean (especially for JSON mode)
            err_console.print(
                f"[dim]AST Reduction: {orig_chars} chars ({int(orig_chars/3.5)} tokens) -> "
                f"{red_chars} chars ({int(red_chars/3.5)} tokens) | "
                f"[bold green]{savings_pct:.1f}% savings[/bold green][/dim]"
            )
            final_content = reduced
        except Exception as e:
            err_console.print(f"[yellow]Warning: AST reduction failed: {e}. Reviewing full file.[/yellow]")
            final_content = content

    # 4. Perform structured LLM review
    try:
        # Show a spinner to stderr while waiting for the LLM
        if json_output:
            result = run_code_review(
                code_content=final_content,
                submission_type=submission_type,
                question=question,
                model=model,
            )
        else:
            with console.status("[bold green]Analyzing submission with Ollama model...[/bold green]"):
                result = run_code_review(
                    code_content=final_content,
                    submission_type=submission_type,
                    question=question,
                    model=model,
                )
    except OllamaConnectionError as e:
        err_console.print(f"[bold red]Connection Error:[/bold red]\n{e}")
        raise typer.Exit(code=1)
    except ReviewError as e:
        err_console.print(f"[bold red]Review Failure:[/bold red]\n{e}")
        raise typer.Exit(code=1)
    except Exception as e:
        err_console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    # 5. Output rendering
    if json_output:
        # Print raw JSON directly to stdout
        sys.stdout.write(result.model_dump_json(indent=2))
        sys.stdout.write("\n")
    else:
        render_rich_output(result)

if __name__ == "__main__":
    app()
