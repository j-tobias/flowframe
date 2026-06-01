from __future__ import annotations

import argparse
import sys

from flowframe.recorder import record


def _resolution(value: str) -> tuple[int, int]:
    try:
        w, h = value.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Resolution must be WIDTHxHEIGHT (e.g. 1920x1080), got: {value!r}"
        )


def _print_help() -> None:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]flowframe[/bold cyan]  [dim]v0.1.0[/dim]\n"
            "[italic dim]Record a smooth-scrolling video of a webpage.[/italic dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()

    console.print("[bold yellow]Usage[/bold yellow]")
    console.print(
        "  flowframe [bold green]--url[/bold green] URL"
        " [bold green]--output[/bold green] FILE"
        " [dim][[bold green]--resolution[/bold green] WxH][/dim]"
        " [dim][[bold green]--scroll-speed[/bold green] PX][/dim]"
    )
    console.print()

    console.print("[bold yellow]Arguments[/bold yellow]")
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), show_edge=False)
    table.add_column("flag", style="bold green", no_wrap=True)
    table.add_column("meta", style="cyan", no_wrap=True)
    table.add_column("description")

    table.add_row(
        "--url",
        "URL",
        "[bold red]required[/bold red]  URL of the webpage to record",
    )
    table.add_row(
        "--output",
        "FILE",
        "[bold red]required[/bold red]  Destination file  [dim].mp4[/dim] or [dim].webm[/dim]",
    )
    table.add_row(
        "--resolution",
        "WxH",
        "Viewport size  [dim]default: 1920x1080[/dim]",
    )
    table.add_row(
        "--scroll-speed",
        "PX",
        "Pixels scrolled per frame at ~60 fps  [dim]default: 4.0[/dim]",
    )
    table.add_row(
        "--wallpaper",
        "",
        "Composite over a macOS-style gradient background with rounded corners and shadow",
    )
    table.add_row(
        "-h, --help",
        "",
        "Show this message and exit",
    )
    console.print(table)

    console.print("[bold yellow]Examples[/bold yellow]")
    console.print("  [dim]# Record a full-page scroll to MP4 (requires ffmpeg)[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://example.com"
        " [green]--output[/green] demo.mp4"
    )
    console.print()
    console.print("  [dim]# 720p WebM with faster scroll — no extra dependencies[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://example.com"
        " [green]--output[/green] demo.webm"
        " [green]--resolution[/green] 1280x720"
        " [green]--scroll-speed[/green] 8"
    )
    console.print()

    console.print("[bold yellow]Notes[/bold yellow]")
    console.print("  [cyan]•[/cyan] A [bold]PDF[/bold] URL is rendered and scrolled just like a web page")
    console.print("  [cyan]•[/cyan] [bold].mp4[/bold] output requires [cyan]ffmpeg[/cyan] on PATH"
                  "  ([dim]apt install ffmpeg[/dim] / [dim]brew install ffmpeg[/dim])")
    console.print("  [cyan]•[/cyan] [bold].webm[/bold] output works without any extra dependencies")
    console.print()


def main() -> None:
    if "--help" in sys.argv or "-h" in sys.argv:
        _print_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(
        prog="flowframe",
        description="Record a smooth-scrolling video of a webpage.",
        add_help=False,
    )
    parser.add_argument("--url", required=True, help="URL of the page to record")
    parser.add_argument("--output", required=True, help="Destination file (.mp4 or .webm)")
    parser.add_argument(
        "--resolution",
        default="1920x1080",
        type=_resolution,
        metavar="WxH",
        help="Viewport size (default: 1920x1080)",
    )
    parser.add_argument(
        "--scroll-speed",
        default=4.0,
        type=float,
        metavar="PX",
        help="Pixels scrolled per frame at ~60fps (default: 4.0)",
    )
    parser.add_argument(
        "--wallpaper",
        action="store_true",
        help="Composite over a macOS-style gradient background with rounded corners and shadow",
    )

    args = parser.parse_args()
    width, height = args.resolution

    print(f"Recording {args.url} → {args.output} ...", flush=True)
    try:
        record(
            url=args.url,
            output=args.output,
            width=width,
            height=height,
            scroll_speed=args.scroll_speed,
            wallpaper=args.wallpaper,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Saved: {args.output}")
