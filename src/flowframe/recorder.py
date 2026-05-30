from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

_WALLPAPER = Path(__file__).parent / "resources" / "13-Ventura-Dark.webp"


def _composite_wallpaper(
    webm_path: Path,
    output_path: Path,
    width: int,
    height: int,
) -> None:
    scale = 0.88
    corner_r = 20   # rounded corner radius (px, in scaled-video space)
    pad = 150       # transparent halo around the shadow silhouette
    sigma = 50      # Gaussian blur sigma; opacity ≈ 0 at pad/2 distance
    sy = 15         # shadow drops this many px below centre

    # Rounded-corner mask: 255 inside the rounded rectangle, 0 in clipped corners.
    # cx/cy = how far into a corner quadrant the pixel is (0 on straight edges).
    cx = f"max(max({corner_r}-X,X-(W-{corner_r})),0)"
    cy = f"max(max({corner_r}-Y,Y-(H-{corner_r})),0)"
    corner_mask = f"if(lte(hypot({cx},{cy}),{corner_r}),255,0)"

    fc = ";".join([
        # Wallpaper: scale to cover the canvas exactly (CSS "cover" behaviour)
        f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}[bg]",
        # Scale recording; convert to rgba; stamp rounded corners into alpha.
        # Long-form option names (red_expr etc.) avoid the r=/r(X,Y) naming clash.
        f"[0:v]scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2[sc]",
        f"[sc]format=rgba,"
        f"geq=red_expr='r(X,Y)':green_expr='g(X,Y)':blue_expr='b(X,Y)':"
        f"alpha_expr='{corner_mask}'[rnd]",
        # Split: one copy for the shadow silhouette, one for the final composite
        f"[rnd]split[rnd1][rnd2]",
        # Shadow: opaque black silhouette → transparent padding → Gaussian blur → 70% opacity
        f"[rnd1]colorchannelmixer=rr=0:gg=0:bb=0[blk]",
        f"[blk]pad=iw+{pad}:ih+{pad}:{pad//2}:{pad//2}:color=black@0[pdd]",
        f"[pdd]gblur=sigma={sigma},colorchannelmixer=aa=0.7[shd]",
        # Composite: wallpaper → shadow (centred, slight y drop) → recording
        f"[bg]format=rgba[bga]",
        f"[bga][shd]overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2+{sy}[bgs]",
        f"[bgs][rnd2]overlay=x=(main_w-overlay_w)/2:y=(main_h-overlay_h)/2",
    ])

    result = subprocess.run(
        ["ffmpeg", "-y",
         "-ss", "1", "-i", str(webm_path),   # skip the loading blank first second
         "-i", str(_WALLPAPER),
         "-filter_complex", fc,
         "-shortest", str(output_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg wallpaper compositing failed (exit {result.returncode}):\n{result.stderr}"
        )


def record(
    url: str,
    output: str,
    width: int = 1920,
    height: int = 1080,
    scroll_speed: float = 4.0,
    wallpaper: bool = False,
) -> None:
    """Record a smooth-scrolling video of a webpage.

    Args:
        url: The page to record.
        output: Destination path — must end in ``.mp4`` or ``.webm``.
        width: Viewport width in pixels.
        height: Viewport height in pixels.
        scroll_speed: Pixels scrolled per frame at ~60 fps.
        wallpaper: Composite the recording over a macOS Ventura desktop wallpaper
            with rounded corners and a soft drop shadow.

    Raises:
        ValueError: If *output* does not end in ``.mp4`` or ``.webm``.
        FileNotFoundError: If ffmpeg is required but not on PATH.
        RuntimeError: If ffmpeg conversion or compositing fails.
    """
    output_path = Path(output)
    suffix = output_path.suffix.lower()

    if suffix not in {".mp4", ".webm"}:
        raise ValueError(
            f"Output must end in .mp4 or .webm, got: {output_path.name!r}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    needs_ffmpeg = suffix == ".mp4" or wallpaper
    if needs_ffmpeg and shutil.which("ffmpeg") is None:
        reason = "--wallpaper" if wallpaper else ".mp4 output"
        raise FileNotFoundError(
            f"ffmpeg is required for {reason} but was not found on PATH.\n"
            "Install it first:\n"
            "  Debian/Ubuntu:  sudo apt install ffmpeg\n"
            "  macOS:          brew install ffmpeg\n"
            "Or record to .webm without --wallpaper to skip this requirement."
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

        if wallpaper:
            _composite_wallpaper(webm_path, output_path, width, height)
        elif suffix == ".webm" and shutil.which("ffmpeg") is None:
            # No ffmpeg available — copy as-is, skip the 1-second trim
            shutil.copy2(webm_path, output_path)
        else:
            # mp4, or webm with ffmpeg available (trim the loading blank first second)
            result = subprocess.run(
                ["ffmpeg", "-y", "-ss", "1", "-i", str(webm_path), str(output_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg conversion failed (exit {result.returncode}):\n{result.stderr}"
                )
