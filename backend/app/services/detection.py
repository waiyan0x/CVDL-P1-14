"""Local YOLO checkpoint adapter; no online weight downloads at startup."""
import numpy as np


class Detector:
    def __init__(self, settings):
        if not settings.detector_path.is_file():
            raise RuntimeError('YOLO checkpoint is missing.')
        import torch
        from ultralytics import YOLO
        torch.set_num_threads(settings.torch_threads)
        self.settings = settings
        self.model = YOLO(str(settings.detector_path))
        self.model.predict(np.zeros((640, 640, 3), np.uint8), device=settings.detector_device, verbose=False)

    def predict(self, image, threshold):
        prediction = self.model.predict(image, device=self.settings.detector_device,
            imgsz=self.settings.detector_image_size, conf=threshold, classes=[1, 2, 3], max_det=30, verbose=False)[0]
        height, width = image.shape[:2]
        fields = []
        for box in prediction.boxes:
            x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
            coordinates = [max(0, min(x1, width - 1)), max(0, min(y1, height - 1)),
                           max(1, min(x2, width)), max(1, min(y2, height))]
            if coordinates[2] > coordinates[0] and coordinates[3] > coordinates[1]:
                fields.append({'label': self.model.names[int(box.cls.item())], 'box': coordinates,
                               'confidence': round(float(box.conf.item()), 4), 'source': 'model'})
        return fields
