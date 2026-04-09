# lenticular-printing

A command-line tool for interlacing multiple images into a single print-ready file for lenticular lens sheets. Configurable lens, printer, and screen profiles let you dial in the exact pixel geometry for your hardware.

Lenticular printing works by interlacing two or more images into alternating columns (or rows), then overlaying a physical lens sheet. Each lens acts as a prism — different images become visible depending on the viewing angle, creating a flip, zoom, or morph effect.

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
git clone https://github.com/johncarges/lenticular-printing.git
cd lenticular-printing
uv sync
```

Verify the install:

```bash
uv run lenticular --help
```

## Workflow

A typical session has three phases:

1. **Set up profiles** — describe your lens sheet and printer once.
2. **Calibrate** — print a test sheet to confirm your lens's true LPI.
3. **Interlace** — process your images for printing.

---

### Step 1 — Create profiles

Profiles are JSON files saved under `profiles/`. A few examples are included; run these commands to build your own.

**Lens sheet**

```bash
uv run lenticular create-lens my_lens \
    --lpi 50.24 \
    --orientation vertical \
    --notes "50 LPI sheet from XYZ supplier"
# → profiles/lenses/my_lens.json
```

**Printer**

```bash
uv run lenticular create-printer my_printer \
    --max-dpi 4800 \
    --paper 13x19 \
    --notes "Canon Pro-100, Photo Paper Plus Glossy II"
# → profiles/printers/my_printer.json
```

Inspect a saved profile at any time:

```bash
uv run lenticular show-lens    profiles/lenses/my_lens.json
uv run lenticular show-printer profiles/printers/my_printer.json
```

---

### Step 2 — Calibrate your lens

Lens sheets rarely match their advertised LPI exactly. This command generates a test print with strips at slightly different LPI values. Print it at actual size, hold the lens flat against the sheet, and tilt slowly — the strip that flips cleanest is your true LPI. Update your lens profile with that value.

```bash
uv run lenticular calibrate \
    --lens profiles/lenses/my_lens.json \
    --printer profiles/printers/my_printer.json \
    --print-width 4 --print-height 6
# → calibration_my_lens.tif
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--strips N` | 8 | Number of test strips |
| `--range FRAC` | 0.12 | LPI bracket as ±fraction of nominal (0.12 = ±12%) |
| `--num-images N` | 2 | Number of images being interlaced |
| `--output FILE` | `calibration_<lens>.tif` | Output path |

---

### Step 3a — Interlace for printing

```bash
uv run lenticular interlace photo_a.jpg photo_b.jpg \
    --lens profiles/lenses/my_lens.json \
    --printer profiles/printers/my_printer.json \
    --print-width 8 --print-height 10 \
    --output result.tif
```

The tool prints a job summary showing computed pixel dimensions and output PPI before processing. Output is saved as TIFF (recommended — lossless, accurate DPI metadata), PNG, or JPEG depending on the file extension you provide.

| Flag | Default | Description |
|------|---------|-------------|
| `--num-images N` | 2 | Number of source images |
| `--print-width IN` | 8.0 | Print width in inches |
| `--print-height IN` | 10.0 | Print height in inches |
| `--output FILE` | `interlaced_<first_image>.tif` | Output path |

**More than two images:** pass all source images as positional arguments and set `--num-images` accordingly.

```bash
uv run lenticular interlace a.jpg b.jpg c.jpg \
    --num-images 3 \
    --lens profiles/lenses/my_lens.json \
    --printer profiles/printers/my_printer.json
```

---

## How it works

Given a lens at **L** LPI and **N** source images:

- Each source image is resized to `(print_width × L)` × `(print_height × L)` pixels.
- The interlaced output is `N` times wider (vertical lenses) or taller (horizontal lenses).
- Output PPI = `L × N`, so the printer renders exactly one column (or row) per lens lenticule.

For vertical lenses, columns alternate: `img0_col0`, `img1_col0`, …, `imgN_col0`, `img0_col1`, …

## Profile reference

### LensProfile (`profiles/lenses/`)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Identifier |
| `lpi` | float | Lines per inch (lenticules per inch) |
| `orientation` | `vertical` \| `horizontal` | Lens orientation |
| `notes` | string | Optional notes |

### PrinterProfile (`profiles/printers/`)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Identifier |
| `max_dpi` | int | Maximum printer DPI |
| `paper_width_in` | float | Maximum paper width in inches |
| `paper_height_in` | float | Maximum paper height in inches |
| `notes` | string | Optional notes (e.g. driver settings, media type) |

## Development

```bash
uv sync --extra dev
uv run pytest
```

> **Note:** `tests/` currently contains reference images but no test files. Contributions welcome.

## Command reference

```
lenticular interlace        Interlace images for printing
lenticular calibrate        Generate a calibration sheet to find true LPI
lenticular create-lens      Create and save a lens profile
lenticular create-printer   Create and save a printer profile
lenticular show-lens        Display a saved lens profile
lenticular show-printer     Display a saved printer profile
```

Run any subcommand with `--help` for full flag details.

---

## Work in progress

### Screen preview

The `screen-preview` command (and the associated `create-screen` / `show-screen` profile commands) are present in the CLI but not reliably usable yet. The feature requires that the screen's physical pixel pitch closely matches the lens LPI — in practice this only works on a narrow range of high-DPI displays. Further work is needed to broaden compatibility and improve the on-screen calibration experience.
