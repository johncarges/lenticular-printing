"""On-screen lenticular preview using a calibrated tkinter window."""
from __future__ import annotations

import tkinter as tk
from PIL import Image, ImageTk
import numpy as np

from .profile import LensProfile, ScreenProfile


def generate_screen_image(
    images: list[Image.Image],
    lens: LensProfile,
    screen: ScreenProfile,
    window_logical_width: int,
    window_logical_height: int,
) -> Image.Image:
    """
    Build an interlaced image sized for 1:1 logical-pixel display.

    Strategy:
      - Each interlaced column = 1 logical pixel = scale_factor physical pixels.
      - This gives `scale_factor` physical pixels per image stripe, and
        `num_images * scale_factor` physical pixels per lens cycle.
      - That's the closest integer fit to the true physical px-per-lens for
        most Retina screens.

    The image is (window_logical_width × window_logical_height) logical pixels,
    which maps to (w * scale_factor × h * scale_factor) physical pixels when
    rendered by a HiDPI-aware window at 100% zoom.
    """
    n = len(images)

    # Each image contributes (window_logical_width // n) logical columns.
    # Integer-divide so the interlaced total == window_logical_width exactly.
    img_logical_w = window_logical_width // n
    # Adjust window width to be exactly divisible
    actual_logical_w = img_logical_w * n

    normalized = []
    for img in images:
        if img.mode != "RGB":
            img = img.convert("RGB")
        normalized.append(img.resize((img_logical_w, window_logical_height), Image.LANCZOS))

    arrays = [np.asarray(img, dtype=np.uint8) for img in normalized]
    h, w, c = arrays[0].shape
    output = np.empty((h, w * n, c), dtype=np.uint8)
    for i, arr in enumerate(arrays):
        output[:, i::n, :] = arr

    return Image.fromarray(output, mode="RGB")


def show_preview(
    image: Image.Image,
    lens: LensProfile,
    screen: ScreenProfile,
    num_images: int,
) -> None:
    """
    Open a tkinter window displaying the image at 1:1 logical pixels.

    On a 2× Retina display this means each image column = 2 physical pixels,
    giving the closest integer alignment to the lens pitch.
    """
    root = tk.Tk()
    root.title(f"Screen Preview — {lens.name}  |  {screen.name}")
    root.resizable(False, False)

    # PhotoImage renders at 1:1 logical pixels; macOS handles Retina scaling.
    photo = ImageTk.PhotoImage(image)

    canvas = tk.Canvas(
        root,
        width=image.width,
        height=image.height,
        highlightthickness=0,
        bg="black",
    )
    canvas.pack(side=tk.TOP)
    canvas.create_image(0, 0, anchor=tk.NW, image=photo)

    stripe = screen.best_stripe_width(lens.lpi, num_images)
    effective_lpi = screen.physical_ppi / (stripe * num_images)
    error_pct = abs(effective_lpi - lens.lpi) / lens.lpi * 100

    status_text = (
        f"Lens {lens.lpi} LPI  ·  "
        f"Screen {screen.physical_ppi:.0f} phys PPI / {screen.logical_ppi:.0f} logical  ·  "
        f"{stripe * num_images} phys px/lens  ·  "
        f"Effective {effective_lpi:.1f} LPI  ·  "
        f"Error {error_pct:.1f}%"
    )
    status = tk.Label(
        root,
        text=status_text,
        anchor="w",
        padx=8,
        pady=4,
        font=("Helvetica", 11),
        bg="#1a1a1a",
        fg="#cccccc",
    )
    status.pack(side=tk.BOTTOM, fill=tk.X)

    root.mainloop()
