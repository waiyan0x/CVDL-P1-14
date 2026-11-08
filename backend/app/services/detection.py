"""Local YOLO checkpoint adapter; no online weight downloads at startup."""
import hashlib
import json
import numpy as np

MODEL_TO_API_LABEL = {
    'front_eds': 'eds',
    'front_eds_num': 'bus_number',
    'front_eds_route': 'route',
    'front_eds_destination': 'destination',
}


class Detector:
    def __init__(self, settings):
        if not settings.detector_path.is_file():
            raise RuntimeError('YOLO checkpoint is missing.')
        if settings.detector_weights is None:
            config_path = settings.root / 'evaluation/object_detection/01760a841333/runs/v4-reviewed-01/detector_config.json'
            expected = json.loads(config_path.read_text(encoding='utf-8'))['checkpoint_sha256']
            digest = hashlib.sha256()
            with settings.detector_path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != expected:
                raise RuntimeError('Default v4 YOLO checkpoint SHA-256 mismatch.')
        import torch
        from ultralytics import YOLO
        torch.set_num_threads(settings.torch_threads)
        self.settings = settings
        self.model = YOLO(str(settings.detector_path))
        names = self.model.names
        actual = [names[index] for index in sorted(names)] if isinstance(names, dict) else list(names)
        expected = list(MODEL_TO_API_LABEL)
        if actual != expected:
            raise RuntimeError(f'YOLO class contract mismatch: expected {expected}, found {actual}.')
        self.model.predict(
            np.zeros((settings.detector_image_size, settings.detector_image_size, 3), np.uint8),
            device=settings.detector_device, imgsz=settings.detector_image_size,
            conf=.50, iou=settings.detector_nms_iou, classes=list(range(4)), max_det=100, verbose=False,
        )

    def predict(self, image, threshold):
        prediction = self.model.predict(image, device=self.settings.detector_device,
            imgsz=self.settings.detector_image_size, conf=threshold, iou=self.settings.detector_nms_iou,
            classes=list(range(4)), max_det=100, verbose=False)[0]
        height, width = image.shape[:2]
        fields = []
        for box in prediction.boxes:
            x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
            coordinates = [max(0, min(x1, width - 1)), max(0, min(y1, height - 1)),
                           max(1, min(x2, width)), max(1, min(y2, height))]
            if coordinates[2] > coordinates[0] and coordinates[3] > coordinates[1]:
                model_label = self.model.names[int(box.cls.item())]
                fields.append({'label': MODEL_TO_API_LABEL[model_label], 'model_label': model_label, 'box': coordinates,
                               'confidence': round(float(box.conf.item()), 4), 'source': 'model'})
        return fields
