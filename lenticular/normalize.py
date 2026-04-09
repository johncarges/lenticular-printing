"""Resize input images to the dimensions required by a LenticularProfile."""
from PIL import Image
from .profile import PrintJob


def normalize_images(
    images: list[Image.Image],
    profile: PrintJob,
    resample: int = Image.LANCZOS,
) -> list[Image.Image]:
    """
    Resize every image to (image_width_px × image_height_px) as defined by
    the profile.  Converts to RGB if needed.

    Args:
        images:   Input PIL images (any size/mode).
        profile:  LenticularProfile defining target dimensions.
        resample: PIL resampling filter (default LANCZOS for highest quality).

    Returns:
        List of RGB images at the correct pixel dimensions.
    """
    target = (profile.image_width_px, profile.image_height_px)
    result = []
    for img in images:
        if img.mode != "RGB":
            img = img.convert("RGB")
        result.append(img.resize(target, resample))
    return result
