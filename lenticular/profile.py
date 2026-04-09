"""Lens sheet, printer, and screen profiles, each independently saveable as JSON."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Lens sheet profile
# ---------------------------------------------------------------------------

@dataclass
class LensProfile:
    """
    Describes a physical lenticular lens sheet.
    Save to profiles/lenses/<name>.json and reuse across print jobs.
    """
    name: str
    lpi: float                      # Lenses per inch (use the exact value, e.g. 50.24)
    orientation: str = "vertical"   # "vertical" (columns) or "horizontal" (rows)
    notes: str = ""                 # Free-form: supplier, thickness, material, etc.

    def __post_init__(self) -> None:
        if self.orientation not in ("vertical", "horizontal"):
            raise ValueError("orientation must be 'vertical' or 'horizontal'")
        if self.lpi <= 0:
            raise ValueError("lpi must be positive")

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "LensProfile":
        return cls(**json.loads(Path(path).read_text()))


# ---------------------------------------------------------------------------
# Printer profile
# ---------------------------------------------------------------------------

@dataclass
class PrinterProfile:
    """
    Describes a printer's capabilities.
    Save to profiles/printers/<name>.json and reuse across print jobs.
    """
    name: str
    max_dpi: int
    paper_width_in: float   # Maximum printable width in inches
    paper_height_in: float  # Maximum printable height in inches
    notes: str = ""         # Free-form: model number, driver quirks, paper type, etc.

    def __post_init__(self) -> None:
        if self.max_dpi <= 0:
            raise ValueError("max_dpi must be positive")
        if self.paper_width_in <= 0 or self.paper_height_in <= 0:
            raise ValueError("paper dimensions must be positive")

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "PrinterProfile":
        return cls(**json.loads(Path(path).read_text()))


# ---------------------------------------------------------------------------
# Runtime job config — combines a lens + printer + job dimensions
# Not saved to disk; constructed on the fly from the two separate profiles.
# ---------------------------------------------------------------------------

@dataclass
class PrintJob:
    """
    Combines a LensProfile and PrinterProfile with job-specific parameters
    (print size, number of images). This is the object the interlace pipeline
    operates on — it is not persisted, just constructed at runtime.
    """
    lens: LensProfile
    printer: PrinterProfile
    num_images: int = 2
    print_width_in: float = 8.0
    print_height_in: float = 10.0

    def __post_init__(self) -> None:
        if self.num_images < 2:
            raise ValueError("num_images must be at least 2")
        if self.print_width_in > self.printer.paper_width_in:
            raise ValueError(
                f"print_width_in ({self.print_width_in}\") exceeds printer paper width "
                f"({self.printer.paper_width_in}\")"
            )
        if self.print_height_in > self.printer.paper_height_in:
            raise ValueError(
                f"print_height_in ({self.print_height_in}\") exceeds printer paper height "
                f"({self.printer.paper_height_in}\")"
            )

    # --- Computed dimensions ---

    @property
    def output_ppi(self) -> float:
        """
        Exact PPI required by lens physics: LPI × number of images.
        Kept as float to avoid accumulating rounding error across the image width.
        """
        return self.lens.lpi * self.num_images

    @property
    def image_width_px(self) -> int:
        """Width each input image must be resized to (1 px per lens column)."""
        return round(self.print_width_in * self.lens.lpi)

    @property
    def image_height_px(self) -> int:
        """Height each input image must be resized to."""
        return round(self.print_height_in * self.output_ppi)

    @property
    def output_width_px(self) -> int:
        """Final interlaced image width in pixels."""
        return self.image_width_px * self.num_images

    @property
    def output_height_px(self) -> int:
        """Final interlaced image height (same as each input image height)."""
        return self.image_height_px

    def summary(self) -> str:
        lines = [
            f"Lens    : {self.lens.name}  ({self.lens.lpi} LPI, {self.lens.orientation})",
            f"Printer : {self.printer.name}  (max {self.printer.max_dpi} DPI, "
            f"{self.printer.paper_width_in}\" × {self.printer.paper_height_in}\" paper)",
            f"Images  : {self.num_images}",
            f"Print   : {self.print_width_in}\" × {self.print_height_in}\"",
            f"Output PPI  : {self.output_ppi:.4f}",
            f"Each input  : {self.image_width_px} × {self.image_height_px} px",
            f"Final output: {self.output_width_px} × {self.output_height_px} px",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Screen profile
# ---------------------------------------------------------------------------

@dataclass
class ScreenProfile:
    """
    Describes a display for on-screen lenticular testing.
    Save to profiles/screens/<name>.json and reuse.

    On HiDPI/Retina displays, scale_factor captures the ratio of physical
    pixels to logical (CSS/point) pixels — typically 2 on Retina Macs.
    """
    name: str
    physical_width_px: int
    physical_height_px: int
    diagonal_in: float
    scale_factor: int = 2       # 1 = standard, 2 = Retina 2×, 3 = Retina 3×
    notes: str = ""

    def __post_init__(self) -> None:
        if self.scale_factor < 1:
            raise ValueError("scale_factor must be >= 1")
        if self.diagonal_in <= 0:
            raise ValueError("diagonal_in must be positive")

    @property
    def physical_ppi(self) -> float:
        """True hardware pixels per inch."""
        diag_px = math.sqrt(self.physical_width_px ** 2 + self.physical_height_px ** 2)
        return diag_px / self.diagonal_in

    @property
    def logical_ppi(self) -> float:
        """Logical (point/CSS pixel) density seen by the OS and apps."""
        return self.physical_ppi / self.scale_factor

    @property
    def logical_width_px(self) -> int:
        return self.physical_width_px // self.scale_factor

    @property
    def logical_height_px(self) -> int:
        return self.physical_height_px // self.scale_factor

    def physical_px_per_lens(self, lpi: float) -> float:
        """Exact physical pixels covered by one lens at this screen's PPI."""
        return self.physical_ppi / lpi

    def best_stripe_width(self, lpi: float, num_images: int) -> int:
        """
        Best integer number of physical pixels per image stripe such that
        num_images stripes fit within one lens as closely as possible.
        Returns physical pixels per image stripe (>= 1).
        """
        px_per_lens = self.physical_px_per_lens(lpi)
        # Try both floor and ceil of px_per_lens / num_images, pick closest
        candidates = [
            max(1, math.floor(px_per_lens / num_images)),
            max(1, math.ceil(px_per_lens / num_images)),
        ]
        return min(candidates, key=lambda c: abs(c * num_images - px_per_lens))

    def calibration_summary(self, lpi: float, num_images: int) -> str:
        px_per_lens = self.physical_px_per_lens(lpi)
        stripe = self.best_stripe_width(lpi, num_images)
        effective_lpi = self.physical_ppi / (stripe * num_images)
        error_pct = abs(effective_lpi - lpi) / lpi * 100
        lines = [
            f"Screen        : {self.name}",
            f"Physical PPI  : {self.physical_ppi:.2f}",
            f"Logical PPI   : {self.logical_ppi:.2f}  (scale {self.scale_factor}×)",
            f"Px per lens   : {px_per_lens:.3f} physical  →  best fit: {stripe * num_images} px ({stripe} per image)",
            f"Effective LPI : {effective_lpi:.2f}  (error {error_pct:.1f}% vs {lpi} LPI)",
        ]
        if error_pct > 5:
            lines.append("  Note: >5% error — effect visible but expect some banding near edges")
        return "\n".join(lines)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "ScreenProfile":
        return cls(**json.loads(Path(path).read_text()))
