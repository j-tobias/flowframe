<p align="center">
  <img src="resources/FlowFrame title.png" alt="FlowFrame" width="100%">
</p>

<div align="center">

[Quick Start](#quick-start) · [CLI Reference](#cli-reference) · [Package API](#package-api) · [Output Formats](#output-formats)

</div>

---

## What is FlowFrame?

FlowFrame records smooth, top-to-bottom scrolling videos of any webpage using a headless browser. Point it at a URL and it captures the full page as it glides from top to bottom at a constant speed — no jitter, no manual recording.

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
flowframe --url URL --output FILE [--resolution WxH] [--scroll-speed PX]
```

| Flag | Default | Description |
|---|---|---|
| `--url` | required | URL of the page to record |
| `--output` | required | Destination file — `.webm` or `.mp4` |
| `--resolution` | `1920x1080` | Viewport size as `WIDTHxHEIGHT` |
| `--scroll-speed` | `4.0` | Pixels scrolled per frame at ~60 fps |

**Examples:**

```bash
# Desktop resolution
flowframe --url https://example.com --output demo.webm

# Vertical (Reels / Shorts)
flowframe --url https://example.com --output demo.webm --resolution 1080x1920

# Slower scroll
flowframe --url https://example.com --output demo.webm --scroll-speed 2
```

---

## Package API

```python
import flowframe as fl

fl.record(url="https://example.com", output="video.webm")

# With options
fl.record(
    url="https://example.com",
    output="video.mp4",
    width=1080,
    height=1920,
    scroll_speed=2.0,
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
- ffmpeg — only required for `.mp4` output
