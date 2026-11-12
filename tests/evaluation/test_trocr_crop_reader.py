"""Check raw decoding, confidence tokens, and explicit generation failures."""

from types import SimpleNamespace
import unittest

import numpy as np
import torch

from backend.app.evaluation.trocr_crop_reader import TrOCRCropReader


class TrOCRReaderTests(unittest.TestCase):
    def reader(self, tokens):
        reader = TrOCRCropReader.__new__(TrOCRCropReader)
        reader.torch, reader.device, reader.max_new_tokens = torch, "cpu", 3
        reader.history = []
        self.processor_calls, self.decode_calls, self.generate_calls = [], [], []
        def process(**kwargs):
            self.processor_calls.append(kwargs)
            return SimpleNamespace(pixel_values=torch.zeros(1, 3, 384, 384))
        def decode(*args, **kwargs):
            self.decode_calls.append(kwargs)
            return [" Ab. "]
        reader.processor = SimpleNamespace(__call__=process)
        class Processor:
            tokenizer = SimpleNamespace(all_special_ids=[0, 1, 2])
            __call__ = staticmethod(process)
            batch_decode = staticmethod(decode)
        reader.processor = Processor()
        def generate(pixels, **kwargs):
            self.generate_calls.append(kwargs)
            return SimpleNamespace(sequences=torch.tensor([[2, *tokens]]),
                                   scores=[torch.zeros(1, 5) for _ in tokens])
        reader.recognizer = SimpleNamespace(generate=generate,
                                           generation_config=SimpleNamespace(eos_token_id=2))
        return reader

    def test_preserve_spaces_case_and_exclude_special_tokens_from_confidence(self):
        reader = self.reader([3, 2])
        output = reader.recognize(np.zeros((12, 60), dtype=np.uint8))
        self.assertEqual(output[0][1], " Ab. ")
        self.assertAlmostEqual(output[0][2], 0.2)
        self.assertEqual(len(reader.history[0]["token_log_probabilities"]), 1)
        self.assertEqual(self.processor_calls[0]["images"].mode, "RGB")
        self.assertEqual(self.processor_calls[0]["images"].size, (60, 12))
        self.assertFalse(self.decode_calls[0]["clean_up_tokenization_spaces"])
        self.assertIsNone(self.generate_calls[0]["forced_eos_token_id"])

    def test_missing_eos_is_error_with_output_retained(self):
        reader = self.reader([3, 4, 3])
        with self.assertRaisesRegex(RuntimeError, "did not emit EOS"):
            reader.recognize(np.zeros((12, 60), dtype=np.uint8))
        self.assertTrue(reader.history[0]["generation_limit_reached"])
        self.assertEqual(reader.history[0]["raw_text"], " Ab. ")

    def test_three_pixel_high_rgb_line_has_explicit_channel_order(self):
        reader = self.reader([3, 2])
        reader.recognize(np.zeros((3, 87), dtype=np.uint8))
        self.assertEqual(self.processor_calls[0]["images"].size, (87, 3))
        self.assertEqual(self.processor_calls[0]["input_data_format"], "channels_last")

    def test_eos_only_has_no_confidence_tokens(self):
        reader = self.reader([2])
        reader.recognize(np.zeros((12, 60), dtype=np.uint8))
        self.assertIsNone(reader.history[0]["token_geometric_mean_confidence"])
        self.assertFalse(reader.history[0]["generation_limit_reached"])


if __name__ == "__main__":
    unittest.main()
