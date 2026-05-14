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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="flowframe",
        description="Record a smooth-scrolling video of a webpage.",
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
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Saved: {args.output}")
