"""Generate a labelled still-photo AVI fixture; this is not real bus footage."""
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[2]
output = ROOT / '.runtime/test-still-video.avi'
source = ROOT / 'data/samples/distance-and-image-quality/eds-cropped-at-the-image-edge.jpg'
image = cv2.imread(str(source))
if image is None:
    raise RuntimeError(f'Could not read the bundled sample: {source}')
image = cv2.resize(image, (960, 640))
cv2.putText(image, 'TEST FIXTURE - STILL PHOTO', (20, 620), cv2.FONT_HERSHEY_SIMPLEX,
            .6, (255, 255, 255), 2)
writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*'MJPG'), 10, (960, 640))
if not writer.isOpened():
    raise RuntimeError('The local OpenCV build could not encode the AVI test fixture.')
for _ in range(100):
    writer.write(image)
writer.release()
print(output)
