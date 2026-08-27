from typing import Dict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

from autoreview.schemas import ReviewResult, Finding

# Initialize a standard rich console
console = Console()

# Styling configurations
SEVERITY_COLORS = {
    "info": "blue",
    "low": "green",
    "medium": "yellow",
    "high": "bright_red",
    "critical": "bold red",
}

RISK_LEVEL_COLORS = {
    "low": "green",
    "medium": "yellow",
    "high": "bright_red",
    "critical": "bold red",
}

CATEGORY_HEADERS = {
    "security": "[bold red]🔴 Security Findings[/bold red]",
    "bug": "[bold yellow]🐛 Logic & Bug Findings[/bold yellow]",
    "architecture": "[bold blue]🏛️ Architectural & Structural Findings[/bold blue]",
    "clean_code": "[bold green]🧼 Clean Code & Style Findings[/bold green]",
    "performance": "[bold magenta]⚡ Performance Findings[/bold magenta]",
}

def render_rich_output(result: ReviewResult) -> None:
    """Pretty-prints the structured code review result in the terminal."""
    
    # 1. Print Overall Summary Panel
    risk_color = RISK_LEVEL_COLORS.get(result.overall_risk_level, "white")
    
    summary_text = Text()
    summary_text.append("Submission Type: ", style="bold")
    summary_text.append(f"{result.submission_type}\n", style="cyan")
    
    summary_text.append("Overall Risk Level: ", style="bold")
    summary_text.append(f"{result.overall_risk_level.upper()}\n\n", style=f"bold {risk_color}")
    
    summary_text.append(result.summary)
    
    console.print(
        Panel(
            summary_text,
            title="[bold white]AutoReview-AI Code Review Summary[/bold white]",
            border_style=risk_color,
            expand=False,
        )
    )
    console.print()

    # 2. Group findings by category
    grouped_findings: Dict[str, list[Finding]] = {
        "security": [],
        "bug": [],
        "architecture": [],
        "clean_code": [],
        "performance": [],
    }
    
    for finding in result.findings:
        cat = finding.category
        if cat in grouped_findings:
            grouped_findings[cat].append(finding)
        else:
            # Fallback for unexpected categories
            grouped_findings.setdefault(cat, []).append(finding)

    # 3. Print a table for each category that has findings
    has_any_findings = False
    
    for category, findings in grouped_findings.items():
        if not findings:
            continue
            
        has_any_findings = True
        header = CATEGORY_HEADERS.get(category, f"[bold]{category.capitalize()} Findings[/bold]")
        
        table = Table(
            title=header,
            title_justify="left",
            show_header=True,
            header_style="bold magenta",
            box=None,
            expand=True,
        )
        
        table.add_column("Severity", width=10)
        table.add_column("Lines", width=8)
        table.add_column("Description", ratio=3)
        table.add_column("Suggestion / Actionable Fix", ratio=3)
        table.add_column("Conf.", width=6, justify="right")
        
        for f in findings:
            sev_color = SEVERITY_COLORS.get(f.severity, "white")
            sev_text = Text(f.severity.upper(), style=f"bold {sev_color}")
            
            # Format lines (e.g. L10-L12 or L10)
            if f.line_start is not None:
                if f.line_end is not None and f.line_end != f.line_start:
                    lines_text = f"L{f.line_start}-{f.line_end}"
                else:
                    lines_text = f"L{f.line_start}"
            else:
                lines_text = "N/A"
                
            conf_pct = f"{int(f.confidence * 100)}%"
            
            table.add_row(
                sev_text,
                lines_text,
                f.description,
                f.suggestion,
                conf_pct,
            )
            
        console.print(table)
        console.print()

    # 4. Success message if no findings detected
    if not has_any_findings:
        console.print(
            Panel(
                "[bold green]No issues or findings detected. Excellent job! Code looks clean and ready.[/bold green]",
                border_style="green",
                expand=False,
            )
        )
