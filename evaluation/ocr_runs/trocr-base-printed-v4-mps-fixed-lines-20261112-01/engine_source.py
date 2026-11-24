"""Untouched public TrOCR line recognizer for the shared crop diagnostic."""

import math

from PIL import Image


class TrOCRCropReader:
    """Expose the shared reader boundary without invoking application adapters."""

    def __init__(self, cache, device, max_new_tokens=64):
        import torch
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        self.processor = TrOCRProcessor.from_pretrained(cache, local_files_only=True, use_fast=False)
        self.recognizer = VisionEncoderDecoderModel.from_pretrained(
            cache, local_files_only=True, use_safetensors=True,
        ).eval().to(device)
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.history = []
        self.torch = torch

    def recognize(self, line, **_shared_reader_options):
        # The shared method supplies a grayscale native-size rectified line.
        # Three identical channels preserve paired upstream preprocessing.
        pixels = self.processor(images=Image.fromarray(line).convert("RGB"),
                                return_tensors="pt").pixel_values.to(self.device)
        output = self.recognizer.generate(
            pixels, do_sample=False, num_beams=1, max_new_tokens=self.max_new_tokens,
            use_cache=True, forced_eos_token_id=None,
            return_dict_in_generate=True, output_scores=True,
        )
        token_ids = output.sequences[0, 1:].tolist()
        eos = self.recognizer.generation_config.eos_token_id
        eos_ids = set(eos if isinstance(eos, list) else [eos])
        text = self.processor.batch_decode(output.sequences, skip_special_tokens=True,
                                           clean_up_tokenization_spaces=False)[0]
        excluded = set(self.processor.tokenizer.all_special_ids)
        log_probs = [float(self.torch.log_softmax(score[0], dim=-1)[token].item())
                     for token, score in zip(token_ids, output.scores) if token not in excluded]
        confidence = math.exp(sum(log_probs)/len(log_probs)) if log_probs else float("nan")
        terminated = any(token in eos_ids for token in token_ids)
        self.history.append({"token_ids": token_ids, "raw_text": text,
                             "token_log_probabilities": log_probs,
                             "token_geometric_mean_confidence": confidence if log_probs else None,
                             "processor_tensor_shape": list(pixels.shape),
                             "eos_observed": terminated,
                             "generation_limit_reached": not terminated})
        if not terminated:
            raise RuntimeError(f"TrOCR did not emit EOS within {self.max_new_tokens} tokens; output retained in engine_history.json")
        return [(None, text, confidence)]
