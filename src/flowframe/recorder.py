from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from flowframe.pdf import render_pdf_to_html, try_load_pdf
from flowframe.utils import (
    build_scroll_script,
    ensure_ffmpeg,
    parse_cookie_string,
    run_ffmpeg,
    validate_output_suffix,
)

_WALLPAPER = Path(__file__).parent / "resources" / "13-Ventura-Dark.webp"


def _composite_wallpaper(
    webm_path: Path,
    output_path: Path,
    width: int,
    height: int,
    max_duration: float | None,
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

    cap = ["-t", str(max_duration)] if max_duration is not None else []
    run_ffmpeg(
        ["-ss", "1", "-i", str(webm_path),   # skip the loading blank first second
         "-i", str(_WALLPAPER),
         "-filter_complex", fc,
         *cap,
         "-shortest", str(output_path)],
        what="wallpaper compositing",
    )


def _resolve_nav_url(url: str, tmp_dir: str, width: int) -> str:
    """Return the URL to navigate to, rendering PDFs to a local HTML page first.

    A PDF URL can't be scrolled in headless Chromium, so it's rasterised into a
    stacked-image HTML page; ordinary URLs pass through unchanged.
    """
    pdf_bytes = try_load_pdf(url)
    if pdf_bytes is None:
        return url
    return render_pdf_to_html(pdf_bytes, Path(tmp_dir) / "pdf", width)


def _capture_scroll(
    nav_url: str,
    tmp_dir: str,
    width: int,
    height: int,
    script: str,
    timeout: float,
    storage_state: str | None = None,
    extra_cookies: list[dict] | None = None,
) -> Path:
    """Open *nav_url*, run the scroll *script*, and return the raw ``.webm`` path."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=tmp_dir,
            record_video_size={"width": width, "height": height},
            storage_state=storage_state,
        )
        if extra_cookies:
            context.add_cookies(extra_cookies)
        page = context.new_page()
        page.set_default_navigation_timeout(timeout)
        page.goto(nav_url, wait_until="networkidle")
        page.evaluate(script)

        # Must read before context.close() — afterwards .video becomes None.
        webm_path = Path(page.video.path())

        context.close()  # flushes and finalises the .webm on disk
        browser.close()

    return webm_path


def _finalize(
    webm_path: Path,
    output_path: Path,
    suffix: str,
    wallpaper: bool,
    width: int,
    height: int,
    max_duration: float | None,
) -> None:
    """Produce the final output from the raw recording.

    Wallpaper compositing and plain ffmpeg conversion (.mp4, or .webm when ffmpeg
    is available) trim the 1s loading lead-in and hard-cap the length to
    *max_duration*. The only path that does neither is a .webm copy made when
    ffmpeg isn't installed — there the scroll-loop cap is the only bound.
    """
    if wallpaper:
        _composite_wallpaper(webm_path, output_path, width, height, max_duration)
    elif suffix == ".webm" and shutil.which("ffmpeg") is None:
        # No ffmpeg available — copy as-is, skip the 1-second trim
        shutil.copy2(webm_path, output_path)
    else:
        # mp4, or webm with ffmpeg available (trim the loading blank first second)
        cap = ["-t", str(max_duration)] if max_duration is not None else []
        run_ffmpeg(
            ["-ss", "1", "-i", str(webm_path), *cap, str(output_path)],
            what="conversion",
        )


def record(
    url: str,
    output: str,
    width: int = 1920,
    height: int = 1080,
    scroll_speed: float = 4.0,
    wallpaper: bool = False,
    max_duration: float | None = None,
    timeout: float = 30000,
    storage_state: str | None = None,
    cookies: list[str] | None = None,
) -> None:
    """Record a smooth-scrolling video of a webpage.

    If *url* points at a PDF (by suffix, ``Content-Type`` or magic bytes), the
    PDF is rasterised into a stacked-image HTML page and scroll-recorded exactly
    like any other page.

    Args:
        url: The page or PDF to record.
        output: Destination path — must end in ``.mp4`` or ``.webm``.
        width: Viewport width in pixels.
        height: Viewport height in pixels.
        scroll_speed: Pixels scrolled per frame at ~60 fps.
        wallpaper: Composite the recording over a macOS Ventura desktop wallpaper
            with rounded corners and a soft drop shadow.
        max_duration: Maximum video length in seconds. When set, scrolling stops
            at the cap even if the page bottom isn't reached (truncate, not
            speed-up). ``None`` records the full page.
        timeout: Navigation timeout in milliseconds for the initial page load.
            Raise this for slow or dynamic pages whose ``networkidle`` never
            settles within the default 30 s.
        storage_state: Path to a Playwright storage-state JSON file (cookies +
            localStorage). Injected into the browser context before navigation so
            the page loads as if already authenticated / consent accepted.
        cookies: List of inline cookie strings in Set-Cookie style,
            e.g. ``["name=value; domain=example.com"]``. Applied on top of any
            *storage_state* that was also provided.

    Raises:
        ValueError: If *output* has an unsupported suffix, *max_duration* <= 0,
            or a cookie string is malformed.
        FileNotFoundError: If ffmpeg is required but not on PATH, or
            *storage_state* path does not exist.
        RuntimeError: If ffmpeg conversion or compositing fails.
    """
    output_path = Path(output)
    suffix = validate_output_suffix(output_path)

    if max_duration is not None and max_duration <= 0:
        raise ValueError(f"max_duration must be positive, got: {max_duration}")

    if timeout < 0:
        raise ValueError(f"timeout must be non-negative, got: {timeout}")

    if storage_state is not None and not Path(storage_state).is_file():
        raise FileNotFoundError(f"--storage-state file not found: {storage_state!r}")

    extra_cookies = [parse_cookie_string(c) for c in cookies] if cookies else None

    if suffix == ".mp4" or wallpaper:
        ensure_ffmpeg("--wallpaper" if wallpaper else ".mp4 output")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    script = build_scroll_script(scroll_speed, max_duration)

    with tempfile.TemporaryDirectory() as tmp_dir:
        nav_url = _resolve_nav_url(url, tmp_dir, width)
        webm_path = _capture_scroll(
            nav_url, tmp_dir, width, height, script, timeout,
            storage_state=storage_state,
            extra_cookies=extra_cookies,
        )
        _finalize(webm_path, output_path, suffix, wallpaper, width, height, max_duration)
