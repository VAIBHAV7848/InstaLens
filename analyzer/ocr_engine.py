"""
OCR engine for extracting text from Instagram screenshots.

Uses pytesseract with OpenCV preprocessing for optimal
text extraction from social media screenshots.
"""

import os
import cv2
import pytesseract
from PIL import Image
import numpy as np


def preprocess_image(image_path: str) -> np.ndarray:
    """
    Preprocess an image for optimal OCR results.

    Steps:
    1. Load image
    2. Resize if too small (improves OCR on small text)
    3. Convert to grayscale
    4. Apply adaptive thresholding for clean text separation
    5. Denoise

    Args:
        image_path: Path to the screenshot image

    Returns:
        Preprocessed image as numpy array
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    # Resize if image is small (helps OCR accuracy)
    height, width = image.shape[:2]
    if width < 800:
        scale = 800 / width
        image = cv2.resize(
            image, None, fx=scale, fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Adaptive thresholding — works well with Instagram's varied backgrounds
    processed = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )

    # Denoise
    processed = cv2.fastNlMeansDenoising(processed, h=10)

    return processed


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from a screenshot image using OCR.

    Args:
        image_path: Path to the screenshot file

    Returns:
        Extracted text as a string
    """
    try:
        processed = preprocess_image(image_path)

        # Use pytesseract with optimal config for social media screenshots
        # --psm 6: Assume a single uniform block of text
        # --oem 3: Use LSTM neural net mode (best accuracy)
        config = "--psm 6 --oem 3"
        text = pytesseract.image_to_string(processed, config=config)

        # Clean up OCR artifacts
        text = clean_ocr_text(text)

        return text

    except Exception as e:
        return f"[OCR Error: {str(e)}]"


def extract_text_from_multiple(image_paths: list[str]) -> list[str]:
    """
    Extract text from multiple screenshot images.

    Args:
        image_paths: List of paths to screenshot files

    Returns:
        List of extracted text strings
    """
    results = []
    for path in image_paths:
        text = extract_text_from_image(path)
        if text and text.strip() and not text.startswith("[OCR Error"):
            results.append(text)
    return results


def clean_ocr_text(text: str) -> str:
    """
    Clean up common OCR artifacts from extracted text.

    - Remove stray single characters
    - Fix common OCR misreads
    - Collapse excessive whitespace/newlines
    """
    import re

    # Remove lines that are just 1-2 characters (OCR noise)
    lines = text.split("\n")
    cleaned_lines = [
        line.strip() for line in lines
        if len(line.strip()) > 2
    ]

    text = "\n".join(cleaned_lines)

    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove common OCR artifacts
    text = re.sub(r"[|}{]", "", text)

    return text.strip()


def is_tesseract_available() -> bool:
    """Check if Tesseract OCR is installed and available."""
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
