"""Lazy, local-only supplied fine-tuned TrOCR adapter."""
class TrOCRAdapter:
    confidence_method = 'generated_token_probability_geometric_mean'

    def __init__(self, settings):
        self.directory = settings.trocr_dir
        weights = self.directory / 'model.safetensors'
        if not weights.is_file() or weights.stat().st_size < 1_000_000:
            raise RuntimeError('Fine-tuned TrOCR weights are missing; prepare the local model cache.')
        self.loaded = None

    def read(self, crop, field):
        import cv2
        import torch
        from PIL import Image
        if self.loaded is None:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            processor = TrOCRProcessor.from_pretrained(str(self.directory), local_files_only=True)
            model = VisionEncoderDecoderModel.from_pretrained(str(self.directory), local_files_only=True).eval()
            device = 'mps' if torch.backends.mps.is_available() else 'cpu'
            model.to(device)
            self.loaded = processor, model, device
        processor, model, device = self.loaded
        image = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        pixels = processor(images=image, return_tensors='pt').pixel_values.to(device)
        with torch.inference_mode():
            output = model.generate(pixels, max_new_tokens=48, return_dict_in_generate=True, output_scores=True)
            scores = model.compute_transition_scores(output.sequences, output.scores, normalize_logits=True)
        raw = processor.batch_decode(output.sequences, skip_special_tokens=True)[0].strip()
        confidence = float(scores.mean().exp().cpu()) if scores.numel() and raw else 0.0
        return raw, confidence
