from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.errors import AppError
from backend.app.media.images import decode_image


def test_known_bundled_avif_sample_decodes_without_allowing_arbitrary_uploads():
    settings = Settings()
    data = (settings.root / 'data/images/test/fce01393-3b0671f0-272.jpg').read_bytes()
    with pytest.raises(AppError) as failure:
        decode_image(data, settings)
    assert failure.value.code == 'unsupported_image'
    image = decode_image(data, settings, trusted_sample=True)
    assert image.shape[2] == 3
    assert max(image.shape[:2]) <= settings.preview_max_side
