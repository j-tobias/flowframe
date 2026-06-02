# flowframe — Implementation Plan

## What it is

A Python package + uv CLI tool that records a smooth-scrolling video of any webpage.
Inspired by HowdyGo, built on Playwright.

---

## Usage

### CLI
```bash
flowframe --url https://example.com --output video.mp4
flowframe --url https://example.com --output video.webm --resolution 1080x1920 --scroll-speed 6
```

### Python package
```python
import flowframe as fl

fl.record(url="https://example.com", output="video.mp4")
fl.record(url="https://example.com", output="video.webm", width=1080, height=1920, scroll_speed=6.0)
```

---

## Options / Parameters

| CLI flag         | Package kwarg   | Default     | Description                                      |
|------------------|-----------------|-------------|--------------------------------------------------|
| `--url`          | `url`           | required    | URL of the webpage to record                     |
| `--output`       | `output`        | required    | Destination path (`.mp4` or `.webm`)             |
| `--resolution`   | `width, height` | `1920x1080` | Resolution as `WIDTHxHEIGHT`                    |
| `--scroll-speed` | `scroll_speed`  | `4.0`       | Pixels scrolled per frame at 60fps               |

---

## Output format behaviour

- Output filename ends in `.webm` → save directly (no extra deps)
- Output filename ends in `.mp4` → convert via `ffmpeg` subprocess after recording
- `ffmpeg` must be installed on the system for `.mp4` output; clear error if missing

---

## File structure

```
src/flowframe/
  __init__.py     # exports: record()
  recorder.py     # core logic (Playwright + optional ffmpeg conversion)
  cli.py          # argparse CLI, entry point for uv tool
```

---

## Implementation details

### recorder.py
1. Launch headless Chromium via Playwright
2. Open a browser context with `record_video_dir` pointed at a `tempfile.TemporaryDirectory`
3. Navigate to URL with `wait_until="networkidle"`
4. Inject a JS `setInterval` loop that scrolls `scroll_speed` px every 16ms (~60fps)
5. Stop when `scrollY + innerHeight >= scrollHeight`
6. Close context → Playwright finalizes the `.webm`
7. If `.mp4` output: run `ffmpeg -y -i <tmp.webm> <output.mp4>` via subprocess
8. Otherwise: copy `.webm` to output path
9. Temp dir cleaned up automatically

### cli.py
- `argparse`-based (stdlib, no extra deps)
- Parses `--resolution` as `WIDTHxHEIGHT` string, splits into `width` / `height` ints
- Calls `recorder.record(...)` and prints a success/error message

### __init__.py
- Exposes `record` so users can `import flowframe as fl; fl.record(...)`

---

## Dependencies

- `playwright>=1.40.0` (Python package)
- Playwright browser binaries: `playwright install chromium` (one-time setup)
- `ffmpeg` system binary (only required for `.mp4` output)

---

## What is NOT in scope (for now)

- Pause at top/bottom before scrolling
- Named resolution presets (e.g. `--resolution mobile`)
- Async API
- Progress bar / live output during recording
