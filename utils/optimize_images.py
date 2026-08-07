#!/usr/bin/env python3
"""
Batch image optimizer.

Examples:
    # Resize images to 50% and save to ./optimized
    python optimize_images.py ./images ./optimized

    # Resize to 40% and use JPEG/WebP quality 65
    python optimize_images.py ./images ./optimized --scale 0.4 --quality 65

    # Process folders recursively
    python optimize_images.py ./images ./optimized --recursive

    # Overwrite originals after creating resized versions
    python optimize_images.py ./images ./images --scale 0.5 --quality 70
"""

from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageOps


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def output_path_for(
    input_path: Path,
    input_root: Path,
    output_root: Path,
) -> Path:
    """
    Preserve the folder structure inside the output directory.
    """
    relative = input_path.relative_to(input_root)
    return output_root / relative


def resize_image(
    input_path: Path,
    output_path: Path,
    scale: float,
    quality: int,
    convert_png_to_jpeg: bool = False,
) -> None:
    """
    Resize and recompress one image.
    """
    with Image.open(input_path) as image:
        # Respect EXIF orientation from phones/cameras.
        image = ImageOps.exif_transpose(image)

        original_width, original_height = image.size

        new_width = max(1, int(original_width * scale))
        new_height = max(1, int(original_height * scale))

        resized = image.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        suffix = output_path.suffix.lower()

        save_kwargs = {}

        if suffix in {".jpg", ".jpeg"}:
            if resized.mode in {"RGBA", "LA", "P"}:
                resized = resized.convert("RGB")

            save_kwargs.update(
                {
                    "quality": quality,
                    "optimize": True,
                    "progressive": True,
                }
            )

        elif suffix == ".webp":
            save_kwargs.update(
                {
                    "quality": quality,
                    "method": 6,
                }
            )

        elif suffix == ".png":
            if convert_png_to_jpeg:
                output_path = output_path.with_suffix(".jpg")
                if resized.mode in {"RGBA", "LA", "P"}:
                    resized = resized.convert("RGB")
                save_kwargs.update(
                    {
                        "quality": quality,
                        "optimize": True,
                        "progressive": True,
                    }
                )
            else:
                save_kwargs.update(
                    {
                        "optimize": True,
                        "compress_level": 9,
                    }
                )

        resized.save(output_path, **save_kwargs)


def find_images(input_dir: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"

    return sorted(
        path
        for path in input_dir.glob(pattern)
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resize and recompress a folder of images."
    )

    parser.add_argument(
        "input_dir",
        type=Path,
        help="Folder containing images to process.",
    )

    parser.add_argument(
        "output_dir",
        type=Path,
        help="Folder where optimized images will be written.",
    )

    parser.add_argument(
        "--scale",
        type=float,
        default=0.5,
        help="Resize scale. Example: 0.5 means half width and half height.",
    )

    parser.add_argument(
        "--quality",
        type=int,
        default=75,
        help="JPEG/WebP quality from 1 to 95. Lower means smaller files.",
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process images in subfolders too.",
    )

    parser.add_argument(
        "--convert-png-to-jpeg",
        action="store_true",
        help="Convert PNG files to JPEG to reduce size more aggressively.",
    )

    args = parser.parse_args()

    input_dir = args.input_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    if not 0 < args.scale <= 1:
        raise SystemExit("--scale must be greater than 0 and less than or equal to 1")

    if not 1 <= args.quality <= 95:
        raise SystemExit("--quality must be between 1 and 95")

    images = find_images(input_dir, args.recursive)

    if not images:
        print(f"No supported images found in {input_dir}")
        return 0

    processed = 0
    failed = 0

    for image_path in images:
        output_path = output_path_for(
            image_path,
            input_dir,
            output_dir,
        )

        try:
            before_size = image_path.stat().st_size

            resize_image(
                image_path,
                output_path,
                scale=args.scale,
                quality=args.quality,
                convert_png_to_jpeg=args.convert_png_to_jpeg,
            )

            final_output_path = (
                output_path.with_suffix(".jpg")
                if image_path.suffix.lower() == ".png"
                and args.convert_png_to_jpeg
                else output_path
            )

            after_size = final_output_path.stat().st_size

            print(
                f"OK: {image_path.name} "
                f"{before_size / 1024:.1f} KB -> {after_size / 1024:.1f} KB"
            )

            processed += 1

        except Exception as exc:
            print(f"FAILED: {image_path} - {type(exc).__name__}: {exc}")
            failed += 1

    print()
    print(f"Processed: {processed}")
    print(f"Failed: {failed}")
    print(f"Output: {output_dir}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
