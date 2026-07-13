"""Resize/compress an image and save it under /data."""
from __future__ import annotations

from core.config import settings
from core.logging import get_logger
from core.security import validate_path
from PIL import Image

logger = get_logger(__name__)


def handle_resize_image(
    input_image_filename: str,
    output_image_filename: str,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int = 50,
) -> str:
    input_path = validate_path(input_image_filename, settings.data_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file {input_image_filename} not found.")

    image = Image.open(input_path)
    if max_width and max_height:
        image.thumbnail((max_width, max_height))

    output_path = validate_path(output_image_filename, settings.data_dir)
    image.save(output_path, format="JPEG", quality=quality)
    return f"Operation 'resize_image' completed: saved to {output_image_filename}."
