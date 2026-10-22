"""Bounded image decoding and coordinate-consistent previews."""
import base64
import io

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from ..errors import AppError


def decode_image(data, settings, *, trusted_sample=False):
    if not data:
        raise AppError(400, 'invalid_image', 'Choose an image to analyse.')
    if len(data) > settings.max_image_bytes:
        raise AppError(413, 'image_too_large', 'Image exceeds the configured upload limit.')
    try:
        with Image.open(io.BytesIO(data)) as original:
            allowed_formats = ('JPEG', 'PNG', 'WEBP', 'AVIF') if trusted_sample else ('JPEG', 'PNG', 'WEBP')
            if original.format not in allowed_formats:
                raise AppError(400, 'unsupported_image', 'Use a JPEG, PNG or WebP image.')
            if original.width * original.height > settings.max_image_pixels:
                raise AppError(413, 'image_too_large', 'Image exceeds the configured pixel limit.')
            image = ImageOps.exif_transpose(original).convert('RGB')
            image.thumbnail((settings.preview_max_side, settings.preview_max_side))
            return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as exc:
        raise AppError(400, 'invalid_image', 'Cannot decode this image. Use JPEG, PNG or WebP.') from exc


def resize_frame(image, maximum):
    height, width = image.shape[:2]
    scale = min(1, maximum / max(height, width))
    return cv2.resize(image, (round(width * scale), round(height * scale))) if scale < 1 else image


def jpeg_data(image):
    ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise AppError(500, 'encoding_error', 'Unable to prepare the processed image.')
    return 'data:image/jpeg;base64,' + base64.b64encode(encoded).decode('ascii')
