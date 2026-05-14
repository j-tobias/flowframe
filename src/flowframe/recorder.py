from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


def record(
    url: str,
    output: str,
    width: int = 1920,
    height: int = 1080,
    scroll_speed: float = 4.0,
) -> None:
    """Record a smooth-scrolling video of a webpage.

    Args:
        url: The page to record.
        output: Destination path — must end in ``.mp4`` or ``.webm``.
        width: Viewport width in pixels.
        height: Viewport height in pixels.
        scroll_speed: Pixels scrolled per frame at ~60 fps.

    Raises:
        ValueError: If *output* does not end in ``.mp4`` or ``.webm``.
        FileNotFoundError: If ``.mp4`` output is requested and ffmpeg is not on PATH.
        RuntimeError: If ffmpeg conversion fails.
    """
    output_path = Path(output)
    suffix = output_path.suffix.lower()

    if suffix not in {".mp4", ".webm"}:
        raise ValueError(
            f"Output must end in .mp4 or .webm, got: {output_path.name!r}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Fail fast before spending time recording.
    if suffix == ".mp4" and shutil.which("ffmpeg") is None:
        raise FileNotFoundError(
            "ffmpeg is required for .mp4 output but was not found on PATH.\n"
            "Install it first:\n"
            "  Debian/Ubuntu:  sudo apt install ffmpeg\n"
            "  macOS:          brew install ffmpeg\n"
            "Or record to .webm to skip this requirement."
        )

    js_scroll = f"""
        () => new Promise((resolve) => {{
            const id = setInterval(() => {{
                window.scrollBy(0, {scroll_speed});
                if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight) {{
                    clearInterval(id);
                    resolve();
                }}
            }}, 16);
        }})
    """

    with tempfile.TemporaryDirectory() as tmp_dir:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": width, "height": height},
                record_video_dir=tmp_dir,
                record_video_size={"width": width, "height": height},
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            page.evaluate(js_scroll)

            # Must read before context.close() — afterwards .video becomes None.
            webm_path = Path(page.video.path())

            context.close()  # flushes and finalises the .webm on disk
            browser.close()

        if suffix == ".webm":
            # copy2 instead of rename: rename fails across device boundaries.
            shutil.copy2(webm_path, output_path)
        else:
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", str(webm_path), str(output_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg conversion failed (exit {result.returncode}):\n{result.stderr}"
                )
