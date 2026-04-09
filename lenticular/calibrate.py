"""
Calibration sheet generator.

Produces a single print with N horizontal strips, each interlaced at a
slightly different effective LPI bracketing the lens's rated value.

Usage:
  Hold the printed sheet behind the lens.
  The strip that flips most cleanly (solid black ↔ solid white) is your
  true LPI — update your lens profile accordingly.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .profile import LensProfile, PrinterProfile


def _make_strip(
    width_px: int,
    height_px: int,
    target_lpi: float,
    image_ppi: float,
    num_images: int,
) -> np.ndarray:
    """
    Build one horizontal strip as an (H, W, 3) uint8 array.

    Column assignment uses a continuous fractional mapping so non-integer
    pixels-per-lens are distributed evenly (Bresenham-style):

        image_idx = floor(x * target_lpi * num_images / image_ppi) % num_images

    Images alternate: 0 = black, 1 = white.
    """
    xs = np.arange(width_px, dtype=np.float64)
    image_indices = np.floor(xs * target_lpi * num_images / image_ppi).astype(int) % num_images
    # Build a row: black columns (0) stay 0, white columns (1) become 255
    row = (image_indices * 255).astype(np.uint8)
    strip = np.stack([row, row, row], axis=-1)           # (W, 3)
    strip = np.broadcast_to(strip, (height_px, width_px, 3)).copy()
    return strip


def generate_calibration_sheet(
    lens: LensProfile,
    print_width_in: float,
    print_height_in: float,
    num_strips: int = 8,
    lpi_range_pct: float = 0.12,
    num_images: int = 2,
) -> Image.Image:
    """
    Generate a calibration sheet image.

    Args:
        lens:            Lens profile (provides the center LPI).
        print_width_in:  Physical print width in inches.
        print_height_in: Physical print height in inches.
        num_strips:      Number of test strips (default 8).
        lpi_range_pct:   Half-width of the LPI bracket as a fraction of
                         lens.lpi (default 0.12 = ±12%).
        num_images:      Number of images to interlace (default 2).

    Returns:
        PIL Image ready to save and print.
    """
    nominal_lpi = lens.lpi
    image_ppi = nominal_lpi * num_images

    W_px = round(print_width_in * image_ppi)
    H_px = round(print_height_in * image_ppi)

    # LPI values to test, evenly spaced across the bracket
    lpi_min = nominal_lpi * (1 - lpi_range_pct)
    lpi_max = nominal_lpi * (1 + lpi_range_pct)
    lpi_values = [
        lpi_min + (lpi_max - lpi_min) * i / (num_strips - 1)
        for i in range(num_strips)
    ]

    # Reserve a label band at the top of each strip (~8% of strip height)
    strip_h_total = H_px // num_strips
    label_h = max(12, round(strip_h_total * 0.14))
    pattern_h = strip_h_total - label_h

    canvas = np.zeros((H_px, W_px, 3), dtype=np.uint8)

    for i, target_lpi in enumerate(lpi_values):
        y0 = i * strip_h_total
        # Label band: mid-grey so text is legible over both black and white
        canvas[y0 : y0 + label_h, :] = 180
        # Pattern band
        strip = _make_strip(W_px, pattern_h, target_lpi, image_ppi, num_images)
        canvas[y0 + label_h : y0 + strip_h_total, :] = strip

    image = Image.fromarray(canvas, mode="RGB")
    draw = ImageDraw.Draw(image)

    # Try to load a small truetype font; fall back to PIL default
    font = None
    font_size = max(10, label_h - 4)
    for family in ("Arial.ttf", "Helvetica.ttf", "DejaVuSans.ttf"):
        try:
            font = ImageFont.truetype(family, size=font_size)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    for i, target_lpi in enumerate(lpi_values):
        y0 = i * strip_h_total
        is_nominal = abs(target_lpi - nominal_lpi) < (lpi_max - lpi_min) / (num_strips * 2)
        marker = " ← target" if is_nominal else ""
        label = f"  {target_lpi:.2f} LPI{marker}"
        draw.text((2, y0 + 2), label, fill=(30, 30, 30), font=font)

    return image
