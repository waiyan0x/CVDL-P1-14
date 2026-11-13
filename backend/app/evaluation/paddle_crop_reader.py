"""Thin recognition-only adapter; Paddle is imported only by the runner."""


class PaddleCropReader:
    def __init__(self, model):
        self.model = model

    def recognize(self, line, **kwargs):
        import numpy as np
        rgb = np.repeat(line[:, :, None], 3, axis=2)
        outputs = list(self.model.predict(input=rgb, batch_size=1))
        if len(outputs) != 1:
            raise ValueError("Expected one Paddle prediction per supplied line")
        result = outputs[0]
        # PaddleX Result is a mapping; do not serialize or parse human-readable repr.
        text, confidence = result["rec_text"], result["rec_score"]
        if not isinstance(text, str):
            raise ValueError("Paddle returned non-string recognition text")
        return [(None, text, float(confidence))]
