"""A8: OCR the credit card number from credit_card.png."""
from __future__ import annotations

import pytesseract
from core.config import settings
from core.logging import get_logger
from core.security import validate_path
from PIL import Image

logger = get_logger(__name__)


def handle_extract_credit_card() -> str:
    input_path = validate_path("credit_card.png", settings.data_dir)
    output_path = validate_path("credit_card.txt", settings.data_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} not found")

    img = Image.open(input_path)
    extracted_text = pytesseract.image_to_string(img)
    card_number = "".join(filter(str.isdigit, extracted_text))
    if not card_number:
        raise ValueError("No valid card number extracted from image.")

    output_path.write_text(card_number, encoding="utf-8")
    return (
        f"Operation 'extract_credit_card' completed: extracted card number {card_number}."
    )
