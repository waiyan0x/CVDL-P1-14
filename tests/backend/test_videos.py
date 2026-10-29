import io

import cv2
import numpy as np
import pytest

from backend.app.config import Settings
from backend.app.errors import AppError
from backend.app.media.videos import VideoStore


def fixture_video(tmp_path):
    path = tmp_path / 'fixture.avi'
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 10, (80, 60))
    assert writer.isOpened()
    for value in range(10):
        writer.write(np.full((60, 80, 3), value * 20, np.uint8))
    writer.release()
    return path.read_bytes()


def test_video_probe_decode_time_and_cleanup(tmp_path):
    store = VideoStore(Settings(root=tmp_path))
    entry = store.add(io.BytesIO(fixture_video(tmp_path)), '../../fixture.avi')
    assert entry['name'] == 'fixture.avi'
    assert entry['duration_ms'] == 1000
    image, actual_ms = store.frame(entry['video_id'], 350)
    assert image.shape == (60, 80, 3)
    assert actual_ms == pytest.approx(300, abs=1)
    store.delete(entry['video_id'])
    store.delete(entry['video_id'])
    with pytest.raises(AppError) as failure:
        store.frame(entry['video_id'], 0)
    assert failure.value.status_code == 404
    assert not list(store.settings.upload_dir.iterdir())


def test_corrupt_and_oversized_videos_do_not_leave_uploads(tmp_path):
    store = VideoStore(Settings(root=tmp_path, max_video_bytes=1024))
    for data, code in [(b'not a video', 400), (b'a' * 1025, 413)]:
        with pytest.raises(AppError) as failure:
            store.add(io.BytesIO(data), 'video.mp4')
        assert failure.value.status_code == code
    assert not list(store.settings.upload_dir.iterdir())


def test_long_video_and_invalid_seek_are_rejected(tmp_path):
    data = fixture_video(tmp_path)
    store = VideoStore(Settings(root=tmp_path, max_video_duration_seconds=.5))
    with pytest.raises(AppError) as failure:
        store.add(io.BytesIO(data), 'fixture.avi')
    assert failure.value.code == 'video_too_long'
    store = VideoStore(Settings(root=tmp_path))
    entry = store.add(io.BytesIO(data), 'fixture.avi')
    with pytest.raises(AppError) as failure:
        store.frame(entry['video_id'], 1000)
    assert failure.value.code == 'timestamp_out_of_range'
    store.close()
