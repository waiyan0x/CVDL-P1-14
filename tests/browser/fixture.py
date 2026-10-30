"""Generate a labelled still-photo AVI fixture; this is not real bus footage."""
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[2]
output = ROOT / '.runtime/test-still-video.avi'
image = cv2.imread(str(ROOT / 'data/samples/01-daylight-329.jpg'))
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
