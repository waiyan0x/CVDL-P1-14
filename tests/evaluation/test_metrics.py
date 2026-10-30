from backend.app.evaluation.metrics import aggregate_engine, score_image, screen_detection_counts


def test_ocr_accuracy_uses_ground_truth_geometry_not_prediction_order():
    truth = [{"id": "left", "box": [0, 0, 100, 40], "bus_number": "3", "destination": "Tampines"},
             {"id": "right", "box": [200, 0, 300, 40], "bus_number": "14", "destination": None}]
    predictions = [{"screen": {"box": [200, 0, 300, 40]}, "fields": {"bus_number": {"raw": "14"}}},
                   {"screen": {"box": [0, 0, 100, 40]}, "fields": {
                       "bus_number": {"raw": "3"}, "destination": {"raw": "tampines"}}}]
    result = score_image(truth, predictions)
    metrics = aggregate_engine([result], [10, 30])
    assert metrics["fields"]["bus_number"]["exact_accuracy"] == 1
    assert metrics["fields"]["destination"]["exact_accuracy"] == 0
    assert metrics["fields"]["destination"]["normalized_accuracy"] == 1
    assert metrics["fields"]["destination"]["normalized_cer"] == 0
    assert metrics["latency_ms"] == {"median": 20, "p95": 29.0, "count": 2}


def test_missing_predictions_count_as_errors_and_empty_ground_truth_is_not_an_invented_score():
    result = score_image([{"id": "one", "box": [0, 0, 100, 40], "bus_number": "123", "destination": None}], [])
    metrics = aggregate_engine([result], [])
    assert metrics["fields"]["bus_number"]["cer"] == 1
    assert metrics["fields"]["bus_number"]["exact_accuracy"] == 0
    assert metrics["fields"]["destination"]["exact_accuracy"] is None
    assert metrics["missed_displays"] == 1


def test_screen_metrics_exclude_estimated_envelopes():
    truth = [{"box": [0, 0, 100, 40]}, {"box": [200, 0, 300, 40]}]
    detections = [{"label": "eds", "source": "field_union", "box": [0, 0, 100, 40]},
                  {"label": "eds", "source": "model", "box": [200, 0, 300, 40]}]
    assert screen_detection_counts(truth, detections) == {
        "true_positive": 1, "false_positive": 0, "false_negative": 1, "excluded_estimates": 1}


def test_partial_field_without_screen_is_associated_using_its_box():
    result = score_image([{"id": "one", "box": [0, 0, 100, 40], "bus_number": "3", "destination": None}],
                         [{"screen": None, "fields": {"bus_number": {"box": [70, 5, 95, 35], "raw": "3"}}}])
    assert result["missed_displays"] == 0
    assert result["displays"][0]["fields"]["bus_number"]["exact"] is True
