<p align="center">
  <img src="resources/FlowFrame title.png" alt="FlowFrame" width="100%">
</p>

<div align="center">

[Quick Start](#quick-start) · [CLI Reference](#cli-reference) · [Package API](#package-api) · [Output Formats](#output-formats)

</div>

---

<video src="resources/github-demo.mp4" autoplay loop muted playsinline width="100%"></video>

---

## What is FlowFrame?

FlowFrame records smooth, top-to-bottom scrolling videos of any webpage using a headless browser. Point it at a URL and it captures the full page as it glides from top to bottom at a constant speed — no jitter, no manual recording.

Point it at a **PDF** URL (or local PDF) and FlowFrame renders every page and scroll-records it just like a web page — same resolution, scroll-speed and `--wallpaper` options apply.

Output is a `.webm` file by default, or a `.mp4` if ffmpeg is available. Resolution and scroll speed are configurable. Works as a CLI tool or as a Python library.

---

## Quick Start

**Install via uv:**

```bash
uv tool install flowframe
playwright install chromium
```

**Record a page:**

```bash
flowframe --url https://example.com --output video.webm
```

---

## CLI Reference

```
flowframe --url URL --output FILE [--resolution WxH] [--scroll-speed PX] [--wallpaper] [--max-duration SECS]
```

| Flag | Default | Description |
|---|---|---|
| `--url` | required | URL of the page to record |
| `--output` | required | Destination file — `.webm` or `.mp4` |
| `--resolution` | `1920x1080` | Viewport size as `WIDTHxHEIGHT` |
| `--scroll-speed` | `4.0` | Pixels scrolled per frame at ~60 fps |
| `--wallpaper` | off | Composite over a macOS desktop wallpaper with rounded corners and shadow |
| `--max-duration` | full page | Cap video length in seconds — truncates the scroll at the cap |

**Examples:**

```bash
# Desktop resolution
flowframe --url https://example.com --output demo.webm

# With macOS wallpaper framing (requires ffmpeg)
flowframe --url https://example.com --output demo.mp4 --wallpaper

# Vertical (Reels / Shorts)
flowframe --url https://example.com --output demo.webm --resolution 1080x1920

# Slower scroll
flowframe --url https://example.com --output demo.webm --scroll-speed 2

# Record a PDF — every page is rendered and scrolled like a web page
flowframe --url https://arxiv.org/pdf/2502.12345 --output paper.webm --scroll-speed 30

# Cap the clip at 10 seconds regardless of page length
flowframe --url https://arxiv.org/pdf/2502.12345 --output paper.webm --max-duration 10
```

> **Tip:** long PDFs stack into a very tall page, so at the default `--scroll-speed 4` a multi-page paper can take several minutes. Bump `--scroll-speed` (e.g. `30`–`40`) for a shorter clip, or set `--max-duration` to hard-cap the length.

---

## Package API

```python
import flowframe as fl

fl.record(url="https://example.com", output="video.webm")

# With wallpaper framing
fl.record(
    url="https://example.com",
    output="video.mp4",
    wallpaper=True,
)

# Full options
fl.record(
    url="https://example.com",
    output="video.mp4",
    width=1080,
    height=1920,
    scroll_speed=2.0,
    wallpaper=True,
    max_duration=10,  # seconds; omit for the full page
)
```

---

## Output Formats

| Format | Requirement | Notes |
|---|---|---|
| `.webm` | Playwright only | No extra dependencies |
| `.mp4` | ffmpeg on PATH | `sudo apt install ffmpeg` · `brew install ffmpeg` |

The output format is determined automatically from the file extension.

---

## Requirements

- Python ≥ 3.13
- [Playwright](https://playwright.dev/python/) — `pip install playwright && playwright install chromium`
- ffmpeg — required for `.mp4` output and `--wallpaper`
- PDF rendering (`pypdfium2`, `pillow`) is bundled — no system packages needed
