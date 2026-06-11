"""Small, dependency-light helpers shared by the recorder.

Kept free of Playwright imports so the pure logic (validation, ffmpeg handling,
scroll-script construction) stays cheap to import and easy to reason about.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

_VALID_SUFFIXES = {".mp4", ".webm"}

# Id of the black element that hides the page while it loads. Installed by the
# recorder's init script, removed by the scroll script, and located in the
# finished video via ffmpeg blackdetect to find the exact trim point.
COVER_ELEMENT_ID = "__flowframe_cover__"


def parse_cookie_string(cookie_str: str) -> dict:
    """Parse a Set-Cookie-style string into a Playwright cookie dict.

    Expected format: ``name=value; domain=example.com[; path=/; ...]``
    At least one of ``domain`` or ``url`` must be present.
    """
    parts = [p.strip() for p in cookie_str.split(";")]
    if not parts or "=" not in parts[0]:
        raise ValueError(
            f"Invalid --cookie value — expected 'name=value[; attr=val ...]', got: {cookie_str!r}"
        )
    name, _, value = parts[0].partition("=")
    cookie: dict = {"name": name.strip(), "value": value}
    for part in parts[1:]:
        if not part:
            continue
        key, _, val = part.partition("=")
        key = key.strip().lower()
        val = val.strip()
        if key == "domain":
            cookie["domain"] = val
        elif key == "path":
            cookie["path"] = val
        elif key == "url":
            cookie["url"] = val
        elif key == "expires":
            try:
                cookie["expires"] = float(val)
            except ValueError:
                pass
        elif key == "httponly":
            cookie["httpOnly"] = True
        elif key == "secure":
            cookie["secure"] = True
        elif key == "samesite":
            cookie["sameSite"] = val
    if "domain" not in cookie and "url" not in cookie:
        raise ValueError(
            f"--cookie must include a domain or url attribute, got: {cookie_str!r}"
        )
    return cookie


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


def probe_video_duration(path: Path) -> float | None:
    """Return the duration of the video at *path* in seconds, or None.

    Returns None when ffprobe is missing or the container reports no duration,
    in which case the caller must fall back to a wall-clock estimate.
    """
    if shutil.which("ffprobe") is None:
        return None
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


_BLACK_INTERVAL_RE = re.compile(r"black_start:(\d+(?:\.\d+)?)\s+black_end:(\d+(?:\.\d+)?)")


def detect_leading_black_end(path: Path) -> float | None:
    """Return when the black loading cover ends in the video at *path*.

    Runs ffmpeg blackdetect and returns the end of the first black interval
    that starts within the first second (the cover is up from the very first
    frame, so a later start means detection picked up something else). Returns
    None when ffmpeg is missing or no such interval exists.
    """
    if shutil.which("ffmpeg") is None:
        return None
    result = subprocess.run(
        ["ffmpeg", "-i", str(path), "-vf", "blackdetect=d=0.2:pix_th=0.10",
         "-an", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    for match in _BLACK_INTERVAL_RE.finditer(result.stderr):
        start, end = float(match.group(1)), float(match.group(2))
        if start <= 1.0:
            return end
    return None


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


def build_scroll_script(
    scroll_speed: float,
    max_duration: float | None,
    pointer: bool = False,
    start_hold_ms: int = 0,
) -> str:
    """Build the JS scroll loop, optionally bounded by a wall-clock deadline.

    Scrolls *scroll_speed* px every ~16ms and resolves once the page bottom is
    reached. When *max_duration* is set, the loop also resolves after that many
    seconds, truncating the recording at the cap. When *pointer* is True, a
    fake mouse cursor is injected and drifts naturally across the viewport.
    *start_hold_ms* keeps the fully-loaded page static before scrolling begins,
    giving the lead-in trim a window of known-good frames to land in.

    The script first removes the loading cover (see ``COVER_ELEMENT_ID``), so
    the black-to-content transition in the video marks the exact moment the
    fully-loaded page becomes visible.
    """
    deadline_ms = "null" if max_duration is None else int(max_duration * 1000)

    pointer_js = ""
    if pointer:
        pointer_js = """
            const _cur = document.createElement('div');
            _cur.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;left:0;top:0;';
            _cur.innerHTML = '<svg viewBox="0 0 14 20" xmlns="http://www.w3.org/2000/svg" style="width:14px;height:20px;filter:drop-shadow(1px 1px 2px rgba(0,0,0,0.55))"><path d="M1,1 L1,17 L5,13 L8,19 L10.5,18 L7.5,12 L13,12 Z" fill="white" stroke="black" stroke-width="1"/></svg>';
            document.body.appendChild(_cur);
            let _px = window.innerWidth * 0.42, _py = window.innerHeight * 0.3;
            let _tx = _px, _ty = _py, _lastMove = Date.now();
            (function _animCur() {
                if (Date.now() - _lastMove > 2200) {
                    _tx = window.innerWidth  * (0.15 + Math.random() * 0.7);
                    _ty = window.innerHeight * (0.10 + Math.random() * 0.8);
                    _lastMove = Date.now();
                }
                _px += (_tx - _px) * 0.035;
                _py += (_ty - _py) * 0.035;
                _cur.style.transform = 'translate(' + _px + 'px,' + _py + 'px)';
                requestAnimationFrame(_animCur);
            })();
        """

    return f"""
        () => new Promise((resolve) => {{
            const cover = document.getElementById('{COVER_ELEMENT_ID}');
            if (cover) cover.remove();
            const start = Date.now();
            const deadlineMs = {deadline_ms};
            {pointer_js}
            setTimeout(() => {{
                const id = setInterval(() => {{
                    window.scrollBy(0, {scroll_speed});
                    const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight;
                    const timedOut = deadlineMs !== null && (Date.now() - start) >= deadlineMs;
                    if (atBottom || timedOut) {{
                        clearInterval(id);
                        resolve();
                    }}
                }}, 16);
            }}, {start_hold_ms});
        }})
    """
