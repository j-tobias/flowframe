from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

from flowframe.recorder import record

try:
    _VERSION = version("flowframe")
except PackageNotFoundError:
    _VERSION = "dev"

_PRESETS: dict[str, dict] = {
    "mobile": {
        "resolution": (390, 844),
        "scroll_speed": 3.0,
        "is_mobile": True,
        "device_scale_factor": 3.0,
        "has_touch": True,
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
        ),
    },
}


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
            f"[bold cyan]flowframe[/bold cyan]  [dim]v{_VERSION}[/dim]\n"
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
        " [dim][[bold green]--preset[/bold green] NAME][/dim]"
        " [dim][[bold green]--resolution[/bold green] WxH][/dim]"
        " [dim][[bold green]--scroll-speed[/bold green] PX][/dim]"
        " [dim][[bold green]--wallpaper[/bold green]][/dim]"
        " [dim][[bold green]--pointer[/bold green]][/dim]"
        " [dim][[bold green]--max-duration[/bold green] SECS][/dim]"
        " [dim][[bold green]--timeout[/bold green] MS][/dim]"
        " [dim][[bold green]--storage-state[/bold green] FILE][/dim]"
        " [dim][[bold green]--cookie[/bold green] STR][/dim]"
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
        "[bold red]required[/bold red]  URL of the webpage [dim](or PDF)[/dim] to record",
    )
    table.add_row(
        "--output",
        "FILE",
        "[bold red]required[/bold red]  Destination file  [dim].mp4[/dim] or [dim].webm[/dim]",
    )
    table.add_row(
        "--preset",
        "NAME",
        "Shorthand config  [dim]mobile[/dim] → 390×844, iPhone UA, touch, 3× DPR",
    )
    table.add_row(
        "--resolution",
        "WxH",
        "Viewport size  [dim]default: 1920x1080  (overrides preset)[/dim]",
    )
    table.add_row(
        "--scroll-speed",
        "PX",
        "Pixels scrolled per frame at ~60 fps  [dim]default: 4.0  (overrides preset)[/dim]",
    )
    table.add_row(
        "--wallpaper",
        "",
        "Composite over a macOS-style gradient background with rounded corners and shadow",
    )
    table.add_row(
        "--pointer",
        "",
        "Overlay an animated fake mouse cursor that drifts naturally across the viewport",
    )
    table.add_row(
        "--max-duration",
        "SECS",
        "Cap video length in seconds  [dim]default: full page[/dim]",
    )
    table.add_row(
        "--timeout",
        "MS",
        "Navigation timeout in milliseconds  [dim]default: 30000[/dim]",
    )
    table.add_row(
        "--storage-state",
        "FILE",
        "Playwright storage-state JSON (cookies + localStorage) injected before load",
    )
    table.add_row(
        "--cookie",
        "STR",
        "Inline cookie  [dim]'name=value; domain=example.com'[/dim]  (repeatable)",
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
    console.print("  [dim]# Mobile-phone viewport with iPhone UA and touch emulation[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://example.com"
        " [green]--output[/green] demo.mp4"
        " [green]--preset[/green] mobile"
    )
    console.print()
    console.print("  [dim]# Add an animated mouse cursor to the recording[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://example.com"
        " [green]--output[/green] demo.mp4"
        " [green]--pointer[/green]"
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
    console.print("  [dim]# Record a PDF — every page rendered and scrolled like a web page[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://arxiv.org/pdf/2502.12345"
        " [green]--output[/green] paper.webm"
        " [green]--scroll-speed[/green] 30"
    )
    console.print()
    console.print("  [dim]# Cap the clip at 10 seconds regardless of page length[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://example.com"
        " [green]--output[/green] demo.webm"
        " [green]--max-duration[/green] 10"
    )
    console.print()
    console.print("  [dim]# Raise the navigation timeout for slow or dynamic pages[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://github.com/org/repo"
        " [green]--output[/green] demo.mp4"
        " [green]--timeout[/green] 90000"
    )
    console.print()
    console.print("  [dim]# Suppress a cookie consent banner via inline cookie[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://example.com"
        " [green]--output[/green] demo.mp4"
        " [green]--cookie[/green] \"cookieconsent_status=dismiss; domain=example.com\""
    )
    console.print()
    console.print("  [dim]# Reuse a saved Playwright storage-state file[/dim]")
    console.print(
        "  flowframe"
        " [green]--url[/green] https://example.com"
        " [green]--output[/green] demo.mp4"
        " [green]--storage-state[/green] ./cookies.json"
    )
    console.print()

    console.print("[bold yellow]Notes[/bold yellow]")
    console.print("  [cyan]•[/cyan] A [bold]PDF[/bold] URL is rendered and scrolled just like a web page")
    console.print("  [cyan]•[/cyan] [bold]--max-duration[/bold] truncates at the cap "
                  "([dim]it does not speed up scrolling to fit[/dim])")
    console.print("  [cyan]•[/cyan] [bold].mp4[/bold] output requires [cyan]ffmpeg[/cyan] on PATH"
                  "  ([dim]apt install ffmpeg[/dim] / [dim]brew install ffmpeg[/dim])")
    console.print("  [cyan]•[/cyan] [bold].webm[/bold] output works without any extra dependencies")
    console.print("  [cyan]•[/cyan] [bold]--cookie[/bold] can be repeated for multiple cookies"
                  "  ([dim]'name=value; domain=...'[/dim])")
    console.print("  [cyan]•[/cyan] [bold]--storage-state[/bold] and [bold]--cookie[/bold] can be combined"
                  "  ([dim]cookies are applied on top[/dim])")
    console.print("  [cyan]•[/cyan] [bold]--preset mobile[/bold] sets 390×844, iPhone UA, 3× DPR, and touch"
                  "  ([dim]--resolution / --scroll-speed override those defaults[/dim])")
    console.print("  [cyan]•[/cyan] [bold]--pointer[/bold] injects a fake cursor via JS — "
                  "headless Chromium does not record the real OS pointer")
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
    parser.add_argument("--url", required=True, help="URL of the page or PDF to record")
    parser.add_argument("--output", required=True, help="Destination file (.mp4 or .webm)")
    parser.add_argument(
        "--preset",
        default=None,
        choices=list(_PRESETS),
        metavar="NAME",
        help=f"Shorthand config ({', '.join(_PRESETS)})",
    )
    parser.add_argument(
        "--resolution",
        default=None,
        type=_resolution,
        metavar="WxH",
        help="Viewport size (default: 1920x1080, or preset value)",
    )
    parser.add_argument(
        "--scroll-speed",
        default=None,
        type=float,
        metavar="PX",
        help="Pixels scrolled per frame at ~60fps (default: 4.0, or preset value)",
    )
    parser.add_argument(
        "--wallpaper",
        action="store_true",
        help="Composite over a macOS-style gradient background with rounded corners and shadow",
    )
    parser.add_argument(
        "--pointer",
        action="store_true",
        help="Overlay an animated fake mouse cursor on the recording",
    )
    parser.add_argument(
        "--max-duration",
        default=None,
        type=float,
        metavar="SECS",
        help="Maximum video length in seconds (default: full page)",
    )
    parser.add_argument(
        "--timeout",
        default=30000,
        type=float,
        metavar="MS",
        help="Navigation timeout in milliseconds (default: 30000)",
    )
    parser.add_argument(
        "--storage-state",
        default=None,
        metavar="FILE",
        help="Playwright storage-state JSON (cookies + localStorage) to inject before navigation",
    )
    parser.add_argument(
        "--cookie",
        action="append",
        metavar="STR",
        help="Inline cookie 'name=value; domain=example.com' (can be repeated)",
    )

    args = parser.parse_args()

    preset = _PRESETS.get(args.preset or "", {})
    resolution = args.resolution or preset.get("resolution") or (1920, 1080)
    scroll_speed = args.scroll_speed if args.scroll_speed is not None else preset.get("scroll_speed", 4.0)
    width, height = resolution

    print(f"Recording {args.url} → {args.output} ...", flush=True)
    try:
        record(
            url=args.url,
            output=args.output,
            width=width,
            height=height,
            scroll_speed=scroll_speed,
            wallpaper=args.wallpaper,
            pointer=args.pointer,
            max_duration=args.max_duration,
            timeout=args.timeout,
            storage_state=args.storage_state,
            cookies=args.cookie,
            is_mobile=preset.get("is_mobile", False),
            device_scale_factor=preset.get("device_scale_factor", 1.0),
            has_touch=preset.get("has_touch", False),
            user_agent=preset.get("user_agent"),
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Saved: {args.output}")
