"""Core lenticular interlacing algorithm."""
import numpy as np
from PIL import Image
from .profile import PrintJob


def interlace(images: list[Image.Image], profile: PrintJob) -> Image.Image:
    """
    Interlace N images into a single lenticular-ready image.

    For vertical lenses (the common case), columns are interleaved:
        output column 0 → image[0] column 0
        output column 1 → image[1] column 0
        output column 2 → image[0] column 1
        output column 3 → image[1] column 1
        ...

    For horizontal lenses, rows are interleaved in the same pattern.

    Args:
        images:  Normalized PIL images — must all be the same size.
        profile: LenticularProfile (used for orientation and validation).

    Returns:
        Interlaced PIL image ready for export.

    Raises:
        ValueError: If images have mismatched sizes or wrong count.
    """
    n = len(images)
    if n < 2:
        raise ValueError("At least 2 images are required for interlacing.")

    arrays = [np.asarray(img, dtype=np.uint8) for img in images]
    h, w, c = arrays[0].shape

    for i, arr in enumerate(arrays[1:], start=1):
        if arr.shape != (h, w, c):
            raise ValueError(
                f"Image {i} has shape {arr.shape}, expected {(h, w, c)}. "
                "Run normalize_images() first."
            )

    if profile.lens.orientation == "vertical":
        # Each image contributes every N-th column
        output = np.empty((h, w * n, c), dtype=np.uint8)
        for i, arr in enumerate(arrays):
            output[:, i::n, :] = arr
    else:
        # Horizontal lenses: interleave rows
        output = np.empty((h * n, w, c), dtype=np.uint8)
        for i, arr in enumerate(arrays):
            output[i::n, :, :] = arr

    return Image.fromarray(output, mode="RGB")
