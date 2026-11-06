import unittest
from unittest.mock import patch

from backend.app.evaluation.seven_segment import (
    cer, check_split_leakage, exact_reading_match, normalize_reading, per_field_match,
    time_gpu_inference,
)


class SevenSegmentEvaluationTests(unittest.TestCase):
    def test_strict_and_normalized_examples(self):
        examples = [
            ("0012", "12", False, True),
            ("− 00.50", "-0.50", False, True),
            ("+07.0", "7.0", False, False),
        ]
        for truth, prediction, strict, normalized in examples:
            with self.subTest(truth=truth, prediction=prediction):
                self.assertIs(exact_reading_match(truth, prediction), strict)
                self.assertIs(exact_reading_match(truth, prediction, normalized=True), normalized)

    def test_cer_uses_hand_counted_edits_and_truth_length(self):
        self.assertEqual(cer("1234", "124"), 1 / 4)  # one deletion
        self.assertEqual(cer("12", "132"), 1 / 2)  # one insertion
        self.assertEqual(cer("12.5", "12.8"), 1 / 4)  # one substitution
        self.assertEqual(cer("0012", "12", normalized=True), 0)
        self.assertEqual(cer("12.0", "12"), 2 / 4)  # decimal and zero remain significant
        self.assertEqual(cer("10", "1O", normalized=True), 1 / 2)  # invalid OCR still scores

    def test_per_field_scores_missing_and_unscored_fields(self):
        scores = per_field_match(
            {"voltage": "0012", "current": "-0.5", "temperature": None},
            {"voltage": "12"},
        )
        self.assertEqual(set(scores), {"voltage", "current"})
        self.assertEqual(scores["voltage"], {"strict_match": False, "normalized_match": True,
                                             "cer": .5, "normalized_cer": 0})
        self.assertEqual(scores["current"], {"strict_match": False, "normalized_match": False,
                                             "cer": 1.0, "normalized_cer": 1.0})

    def test_normalizer_keeps_sign_and_decimal_precision(self):
        self.assertEqual(normalize_reading("-000.50"), "-0.50")
        self.assertEqual(normalize_reading("+000"), "+0")
        self.assertEqual(normalize_reading("12 34"), "1234")  # one crop is one reading
        self.assertNotEqual(normalize_reading("12.0"), normalize_reading("12"))
        self.assertNotEqual(normalize_reading("-0"), normalize_reading("0"))
        with self.assertRaises(ValueError):
            normalize_reading("1.2.3")
        with self.assertRaises(ValueError):
            cer("", "7")

    def test_split_leakage_catches_display_reuse_and_adjacent_frames(self):
        samples = [
            {"split": "train", "display_group_id": "meter-a", "recording_id": "clip-1", "frame_index": 100},
            {"split": "val", "display_group_id": "meter-a", "recording_id": "clip-2", "frame_index": 7},
            {"split": "test", "display_group_id": "meter-b", "recording_id": "clip-1", "frame_index": 101},
        ]
        issues = check_split_leakage(samples)
        self.assertTrue(any("display meter-a" in issue for issue in issues))
        self.assertTrue(any("recording clip-1 frames 100/101" in issue for issue in issues))
        clean = [dict(samples[0]), {"split": "test", "display_group_id": "meter-b",
                                    "recording_id": "clip-3", "frame_index": 101}]
        self.assertEqual(check_split_leakage(clean), [])
        nonconsecutive = [dict(samples[0]), {"split": "test", "display_group_id": "meter-b",
                                            "recording_id": "clip-1", "frame_index": 500}]
        self.assertTrue(any("recording clip-1 appears" in issue for issue in check_split_leakage(nonconsecutive)))

    def test_cuda_timer_excludes_warmup_and_records_gpu_name(self):
        calls = []

        class FakeEvent:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def record(self):
                pass

            def synchronize(self):
                pass

            def elapsed_time(self, other):
                return 4.0

        class FakeCuda:
            Event = FakeEvent

            @staticmethod
            def device(index):
                return FakeMode()

            @staticmethod
            def is_available():
                return True

            @staticmethod
            def get_device_name(index):
                return "Test GPU"

            @staticmethod
            def synchronize(index):
                pass

        class FakeMode:
            def __enter__(self):
                pass

            def __exit__(self, *args):
                pass

        class FakeTorch:
            cuda = FakeCuda()

            @staticmethod
            def inference_mode():
                return FakeMode()

        result = time_gpu_inference(lambda: calls.append(1), warmup_runs=2,
                                    timed_runs=3, torch_module=FakeTorch())
        self.assertEqual(len(calls), 5)
        self.assertEqual(result["warmup_runs"], 2)
        self.assertEqual(result["samples_ms"], [4.0, 4.0, 4.0])
        self.assertEqual(result["gpu_model"], "Test GPU")
        self.assertEqual(result["latency_ms_median"], 4.0)
        self.assertEqual(result["latency_ms_p95"], 4.0)
        self.assertEqual(result["timing_method"], "cuda_events")

    def test_mps_timer_synchronizes_and_records_model(self):
        calls = []

        class FakeMps:
            @staticmethod
            def synchronize():
                calls.append("sync")

            @staticmethod
            def is_available():
                return True

        class FakeBackends:
            mps = FakeMps()

        class FakeMode:
            def __enter__(self):
                pass

            def __exit__(self, *args):
                pass

        class FakeTorch:
            mps = FakeMps()
            backends = FakeBackends()

            @staticmethod
            def inference_mode():
                return FakeMode()

        with patch("backend.app.evaluation.seven_segment._mps_gpu_model", return_value="Apple M1"), \
             patch("backend.app.evaluation.seven_segment.perf_counter", side_effect=[1.0, 1.004, 2.0, 2.006]):
            result = time_gpu_inference(lambda: calls.append("infer"), device="mps",
                                        warmup_runs=1, timed_runs=2, torch_module=FakeTorch())
        self.assertEqual(calls, ["infer", "sync", "infer", "sync", "infer", "sync"])
        self.assertEqual(result["gpu_model"], "Apple M1")
        self.assertAlmostEqual(result["samples_ms"][0], 4.0)
        self.assertAlmostEqual(result["samples_ms"][1], 6.0)
        self.assertEqual(result["timing_method"], "synchronized_wall_clock")


if __name__ == "__main__":
    unittest.main()
