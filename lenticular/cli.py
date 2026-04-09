"""Command-line interface for lenticular print interlacing."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from .calibrate import generate_calibration_sheet
from .export import save_interlaced
from .interlace import interlace
from .normalize import normalize_images
from .profile import LensProfile, PrinterProfile, PrintJob, ScreenProfile
from .screen_preview import generate_screen_image, show_preview


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_interlace(args: argparse.Namespace) -> None:
    lens = LensProfile.load(args.lens)
    printer = PrinterProfile.load(args.printer)
    job = PrintJob(
        lens=lens,
        printer=printer,
        num_images=args.num_images,
        print_width_in=args.print_width,
        print_height_in=args.print_height,
    )

    print(job.summary())
    print()

    if len(args.images) != job.num_images:
        print(
            f"Warning: --num-images is {job.num_images} "
            f"but {len(args.images)} image(s) provided.",
            file=sys.stderr,
        )

    images = []
    for p in args.images:
        img = Image.open(p)
        print(f"  Loaded {p}  ({img.width}×{img.height} px, {img.mode})")
        images.append(img)

    print(f"\nResizing to {job.image_width_px}×{job.image_height_px} px each…")
    normalized = normalize_images(images, job)

    print(f"Interlacing ({job.lens.orientation} lenses)…")
    result = interlace(normalized, job)

    output_path = args.output or f"interlaced_{Path(args.images[0]).stem}.tif"
    saved = save_interlaced(result, output_path, job)
    print(f"\nSaved → {saved}  ({result.width}×{result.height} px @ {job.output_ppi:.4f} PPI)")


def cmd_calibrate(args: argparse.Namespace) -> None:
    lens = LensProfile.load(args.lens)
    printer = PrinterProfile.load(args.printer)

    lpi_min = lens.lpi * (1 - args.range)
    lpi_max = lens.lpi * (1 + args.range)
    print(f"Generating calibration sheet:")
    print(f"  Lens    : {lens.name}  ({lens.lpi} LPI nominal)")
    print(f"  LPI range: {lpi_min:.2f} – {lpi_max:.2f}  ({args.strips} strips)")
    print(f"  Size    : {args.print_width}\" × {args.print_height}\"")
    print()

    sheet = generate_calibration_sheet(
        lens=lens,
        print_width_in=args.print_width,
        print_height_in=args.print_height,
        num_strips=args.strips,
        lpi_range_pct=args.range,
        num_images=args.num_images,
    )

    output_path = args.output or f"calibration_{lens.name}.tif"
    dpi = lens.lpi * args.num_images
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, dpi=(dpi, dpi), compression="tiff_lzw")
    print(f"Saved → {path}  ({sheet.width}×{sheet.height} px @ {dpi:.2f} PPI)")
    print()
    print("Print at actual size, then hold the lens flat against the sheet.")
    print("Tilt slowly — the strip that flips cleanest is your true LPI.")
    print("Update your lens profile with that value.")


def cmd_screen_preview(args: argparse.Namespace) -> None:
    lens = LensProfile.load(args.lens)
    screen = ScreenProfile.load(args.screen)
    num_images = args.num_images

    print(screen.calibration_summary(lens.lpi, num_images))
    print()

    if len(args.images) != num_images:
        print(
            f"Warning: --num-images is {num_images} "
            f"but {len(args.images)} image(s) provided.",
            file=sys.stderr,
        )

    images = []
    for p in args.images:
        img = Image.open(p)
        print(f"  Loaded {p}  ({img.width}×{img.height} px, {img.mode})")
        images.append(img)

    w = args.width or round(screen.logical_width_px * 0.85)
    h = args.height or round(screen.logical_height_px * 0.85)

    print(f"\nGenerating screen preview at {w}×{h} logical px…")
    preview_img = generate_screen_image(images, lens, screen, w, h)
    print("Opening preview window — hold lens against screen and tilt to test.\n")
    show_preview(preview_img, lens, screen, num_images)


def cmd_create_lens(args: argparse.Namespace) -> None:
    lens = LensProfile(
        name=args.name,
        lpi=args.lpi,
        orientation=args.orientation,
        notes=args.notes or "",
    )
    out_path = Path(args.dir) / f"{args.name}.json"
    lens.save(out_path)
    print(f"Lens profile saved → {out_path}")
    print(f"  LPI         : {lens.lpi}")
    print(f"  Orientation : {lens.orientation}")
    if lens.notes:
        print(f"  Notes       : {lens.notes}")


def cmd_create_printer(args: argparse.Namespace) -> None:
    paper_w, paper_h = (float(v) for v in args.paper.split("x"))
    printer = PrinterProfile(
        name=args.name,
        max_dpi=args.max_dpi,
        paper_width_in=paper_w,
        paper_height_in=paper_h,
        notes=args.notes or "",
    )
    out_path = Path(args.dir) / f"{args.name}.json"
    printer.save(out_path)
    print(f"Printer profile saved → {out_path}")
    print(f"  Name    : {printer.name}")
    print(f"  Max DPI : {printer.max_dpi}")
    print(f"  Paper   : {printer.paper_width_in}\" × {printer.paper_height_in}\"")
    if printer.notes:
        print(f"  Notes   : {printer.notes}")


def cmd_create_screen(args: argparse.Namespace) -> None:
    res_w, res_h = (int(v) for v in args.physical_res.split("x"))
    screen = ScreenProfile(
        name=args.name,
        physical_width_px=res_w,
        physical_height_px=res_h,
        diagonal_in=args.diagonal,
        scale_factor=args.scale_factor,
        notes=args.notes or "",
    )
    out_path = Path(args.dir) / f"{args.name}.json"
    screen.save(out_path)
    print(f"Screen profile saved → {out_path}")
    print(f"  Physical    : {screen.physical_width_px}×{screen.physical_height_px} px")
    print(f"  Diagonal    : {screen.diagonal_in}\"")
    print(f"  Physical PPI: {screen.physical_ppi:.2f}")
    print(f"  Logical PPI : {screen.logical_ppi:.2f}  (scale {screen.scale_factor}×)")


def cmd_show_lens(args: argparse.Namespace) -> None:
    lens = LensProfile.load(args.profile)
    print(f"Lens profile : {lens.name}")
    print(f"  LPI         : {lens.lpi}")
    print(f"  Orientation : {lens.orientation}")
    if lens.notes:
        print(f"  Notes       : {lens.notes}")


def cmd_show_printer(args: argparse.Namespace) -> None:
    printer = PrinterProfile.load(args.profile)
    print(f"Printer profile : {printer.name}")
    print(f"  Max DPI : {printer.max_dpi}")
    print(f"  Paper   : {printer.paper_width_in}\" × {printer.paper_height_in}\"")
    if printer.notes:
        print(f"  Notes   : {printer.notes}")


def cmd_show_screen(args: argparse.Namespace) -> None:
    screen = ScreenProfile.load(args.profile)
    print(f"Screen profile : {screen.name}")
    print(f"  Physical    : {screen.physical_width_px}×{screen.physical_height_px} px")
    print(f"  Diagonal    : {screen.diagonal_in}\"")
    print(f"  Physical PPI: {screen.physical_ppi:.2f}")
    print(f"  Logical PPI : {screen.logical_ppi:.2f}  (scale {screen.scale_factor}×)")
    if screen.notes:
        print(f"  Notes       : {screen.notes}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lenticular",
        description="Lenticular print interlacing tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create profiles
  uv run lenticular create-lens 50_24lpi --lpi 50.24 --notes "Advertised 50 LPI, package says 50.24"
  uv run lenticular create-printer my_printer --max-dpi 4800 --paper 13x19
  uv run lenticular create-screen imac_5k_27 --physical-res 5120x2880 --diagonal 27 --scale-factor 2

  # Interlace for printing
  uv run lenticular interlace photo_a.jpg photo_b.jpg \\
      --lens profiles/lenses/50_24lpi.json \\
      --printer profiles/printers/my_printer.json \\
      --print-width 8 --print-height 10 --output result.tif

  # On-screen test (hold lens against monitor)
  uv run lenticular screen-preview photo_a.jpg photo_b.jpg \\
      --lens profiles/lenses/50_24lpi.json \\
      --screen profiles/screens/imac_5k_27.json
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- interlace ---
    p_int = sub.add_parser("interlace", help="Interlace images for printing")
    p_int.add_argument("images", nargs="+", metavar="IMAGE")
    p_int.add_argument("--lens", required=True, metavar="JSON")
    p_int.add_argument("--printer", required=True, metavar="JSON")
    p_int.add_argument("--num-images", type=int, default=2, metavar="N")
    p_int.add_argument("--print-width", type=float, default=8.0, metavar="IN")
    p_int.add_argument("--print-height", type=float, default=10.0, metavar="IN")
    p_int.add_argument("--output", "-o", metavar="FILE")

    # --- calibrate ---
    p_cal = sub.add_parser("calibrate", help="Print a calibration sheet to find your true LPI")
    p_cal.add_argument("--lens", required=True, metavar="JSON")
    p_cal.add_argument("--printer", required=True, metavar="JSON")
    p_cal.add_argument("--print-width", type=float, default=4.0, metavar="IN")
    p_cal.add_argument("--print-height", type=float, default=6.0, metavar="IN")
    p_cal.add_argument("--strips", type=int, default=8, metavar="N",
                       help="Number of test strips (default: 8)")
    p_cal.add_argument("--range", type=float, default=0.12, metavar="FRAC",
                       help="LPI bracket as fraction of nominal, e.g. 0.12 = ±12%% (default: 0.12)")
    p_cal.add_argument("--num-images", type=int, default=2, metavar="N")
    p_cal.add_argument("--output", "-o", metavar="FILE",
                       help="Output file (default: calibration_<lens>.tif)")

    # --- screen-preview ---
    p_sp = sub.add_parser("screen-preview", help="On-screen test (hold lens against monitor)")
    p_sp.add_argument("images", nargs="+", metavar="IMAGE")
    p_sp.add_argument("--lens", required=True, metavar="JSON")
    p_sp.add_argument("--screen", required=True, metavar="JSON")
    p_sp.add_argument("--num-images", type=int, default=2, metavar="N")
    p_sp.add_argument("--width", type=int, default=None, metavar="PX",
                      help="Window width in logical pixels (default: 85%% of screen)")
    p_sp.add_argument("--height", type=int, default=None, metavar="PX",
                      help="Window height in logical pixels (default: 85%% of screen)")

    # --- create-lens ---
    p_lens = sub.add_parser("create-lens", help="Create and save a lens sheet profile")
    p_lens.add_argument("name")
    p_lens.add_argument("--lpi", type=float, required=True)
    p_lens.add_argument("--orientation", choices=["vertical", "horizontal"], default="vertical")
    p_lens.add_argument("--notes", metavar="TEXT")
    p_lens.add_argument("--dir", default="profiles/lenses", metavar="DIR")

    # --- create-printer ---
    p_printer = sub.add_parser("create-printer", help="Create and save a printer profile")
    p_printer.add_argument("name")
    p_printer.add_argument("--max-dpi", type=int, required=True, metavar="DPI")
    p_printer.add_argument("--paper", required=True, metavar="WxH")
    p_printer.add_argument("--notes", metavar="TEXT")
    p_printer.add_argument("--dir", default="profiles/printers", metavar="DIR")

    # --- create-screen ---
    p_screen = sub.add_parser("create-screen", help="Create and save a screen/display profile")
    p_screen.add_argument("name")
    p_screen.add_argument("--physical-res", required=True, metavar="WxH",
                          help="Physical pixel resolution, e.g. 5120x2880")
    p_screen.add_argument("--diagonal", type=float, required=True, metavar="IN",
                          help="Screen diagonal in inches")
    p_screen.add_argument("--scale-factor", type=int, default=2, metavar="N",
                          help="HiDPI scale factor (1=standard, 2=Retina 2x, default: 2)")
    p_screen.add_argument("--notes", metavar="TEXT")
    p_screen.add_argument("--dir", default="profiles/screens", metavar="DIR")

    # --- show-lens / show-printer / show-screen ---
    for name, help_text in [
        ("show-lens", "Display a saved lens profile"),
        ("show-printer", "Display a saved printer profile"),
        ("show-screen", "Display a saved screen profile"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("profile", metavar="JSON")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "interlace": cmd_interlace,
        "calibrate": cmd_calibrate,
        "screen-preview": cmd_screen_preview,
        "create-lens": cmd_create_lens,
        "create-printer": cmd_create_printer,
        "create-screen": cmd_create_screen,
        "show-lens": cmd_show_lens,
        "show-printer": cmd_show_printer,
        "show-screen": cmd_show_screen,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
