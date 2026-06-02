"""Small, dependency-light helpers shared by the recorder.

Kept free of Playwright imports so the pure logic (validation, ffmpeg handling,
scroll-script construction) stays cheap to import and easy to reason about.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_VALID_SUFFIXES = {".mp4", ".webm"}


def validate_output_suffix(output: Path) -> str:
    """Return the lowercased output suffix, or raise if it isn't supported."""
    suffix = output.suffix.lower()
    if suffix not in _VALID_SUFFIXES:
        raise ValueError(f"Output must end in .mp4 or .webm, got: {output.name!r}")
    return suffix


def ensure_ffmpeg(reason: str) -> None:
    """Raise ``FileNotFoundError`` with install hints if ffmpeg isn't on PATH.

    *reason* names the feature that needs ffmpeg (e.g. ``".mp4 output"``).
    """
    if shutil.which("ffmpeg") is not None:
        return
    raise FileNotFoundError(
        f"ffmpeg is required for {reason} but was not found on PATH.\n"
        "Install it first:\n"
        "  Debian/Ubuntu:  sudo apt install ffmpeg\n"
        "  macOS:          brew install ffmpeg\n"
        "Or record to .webm without --wallpaper to skip this requirement."
    )


def run_ffmpeg(args: list[str], *, what: str) -> None:
    """Run ``ffmpeg <args>``, raising ``RuntimeError`` on a non-zero exit.

    *what* describes the operation for the error message (e.g. ``"conversion"``).
    """
    result = subprocess.run(
        ["ffmpeg", "-y", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg {what} failed (exit {result.returncode}):\n{result.stderr}"
        )


def build_scroll_script(scroll_speed: float, max_duration: float | None) -> str:
    """Build the JS scroll loop, optionally bounded by a wall-clock deadline.

    Scrolls *scroll_speed* px every ~16ms and resolves once the page bottom is
    reached. When *max_duration* is set, the loop also resolves after that many
    seconds, truncating the recording at the cap.
    """
    deadline_ms = "null" if max_duration is None else int(max_duration * 1000)
    return f"""
        () => new Promise((resolve) => {{
            const start = Date.now();
            const deadlineMs = {deadline_ms};
            const id = setInterval(() => {{
                window.scrollBy(0, {scroll_speed});
                const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight;
                const timedOut = deadlineMs !== null && (Date.now() - start) >= deadlineMs;
                if (atBottom || timedOut) {{
                    clearInterval(id);
                    resolve();
                }}
            }}, 16);
        }})
    """
