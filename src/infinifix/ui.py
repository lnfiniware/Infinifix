from __future__ import annotations

from typing import Iterable, Mapping

from rich.box import HEAVY
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme


def build_console() -> Console:
    theme = Theme(
        {
            "accent": "bold #cf1020",
            "ok": "bold #ffffff",
            "warn": "bold #cf1020",
            "muted": "#aaaaaa",
            "panel": "white on #0b0b0b",
        }
    )
    return Console(theme=theme)


def banner(console: Console) -> None:
    title = "[accent]InfiniFix[/accent]  [muted]Huawei Linux Doctor[/muted]"
    console.print(
        Panel(
            title,
            subtitle="Infiniware",
            border_style="accent",
            box=HEAVY,
            style="panel",
        )
    )


def summary_table(console: Console, summary: Mapping[str, str]) -> None:
    table = Table(title="System Summary", box=HEAVY, border_style="accent")
    table.add_column("Key", style="accent")
    table.add_column("Value", style="ok")
    for key, value in summary.items():
        table.add_row(key, value)
    console.print(table)


def actions_table(console: Console, actions: Iterable[Mapping[str, object]]) -> None:
    table = Table(title="Plan", box=HEAVY, border_style="accent")
    table.add_column("Module", style="accent")
    table.add_column("Action", style="ok")
    table.add_column("Level", style="muted")
    for action in actions:
        level = "advanced" if action.get("advanced") else "safe"
        table.add_row(str(action.get("module", "?")), str(action.get("description", "")), level)
    console.print(table)


def results_table(console: Console, title: str, rows: Iterable[Mapping[str, object]]) -> None:
    table = Table(title=title, box=HEAVY, border_style="accent")
    table.add_column("Module", style="accent")
    table.add_column("Item", style="ok")
    table.add_column("Status", style="ok")
    table.add_column("Detail", style="muted")
    for row in rows:
        table.add_row(
            str(row.get("module", "?")),
            str(row.get("id", "?")),
            str(row.get("status", "unknown")),
            str(row.get("message", "")),
        )
    console.print(table)


def line(console: Console, message: str, style: str = "ok") -> None:
    console.print(message, style=style)

