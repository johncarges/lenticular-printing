"""Save the interlaced image with correct DPI metadata for printing."""
from pathlib import Path
from PIL import Image
from .profile import PrintJob


def save_interlaced(
    image: Image.Image,
    output_path: str | Path,
    profile: PrintJob,
) -> Path:
    """
    Save the interlaced image with DPI metadata embedded.

    Format is inferred from the file extension:
      .tif / .tiff  — LZW-compressed TIFF (recommended: lossless, exact DPI)
      .png          — lossless PNG
      .jpg / .jpeg  — high-quality JPEG (lossy, but widely accepted by printers)

    Args:
        image:       The interlaced PIL image.
        output_path: Destination file path.
        profile:     LenticularProfile (used for DPI metadata).

    Returns:
        Resolved output Path.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    dpi = (profile.output_ppi, profile.output_ppi)
    ext = path.suffix.lower()

    if ext in (".tif", ".tiff"):
        image.save(path, dpi=dpi, compression="tiff_lzw")
    elif ext == ".png":
        image.save(path, dpi=dpi)
    elif ext in (".jpg", ".jpeg"):
        image.save(path, dpi=dpi, quality=95, subsampling=0)
    else:
        # Fall back to TIFF for unknown extensions
        path = path.with_suffix(".tif")
        image.save(path, dpi=dpi, compression="tiff_lzw")

    return path
