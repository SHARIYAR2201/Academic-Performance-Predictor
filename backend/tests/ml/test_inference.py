import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.inference_service import (  # noqa: E402
    get_registry,
    predict_for_student,
    risk_level_from_category,
)

SAMPLE_FEATURES = {
    "previous_gpa": 3.0,
    "previous_semester_gpa": 2.9,
    "attendance_percentage": 85.0,
    "quiz_avg": 78.0,
    "assignment_avg": 80.0,
    "midterm_score": 75.0,
    "project_score": 82.0,
    "lab_score": 88.0,
    "completed_courses": 12,
    "credit_load": 15,
    "historical_trend": 0,
}


def test_registry_loads_real_artifacts():
    registry = get_registry()
    assert registry.classification_model is not None
    assert registry.regression_model is not None
    assert len(registry.class_labels) == 4
    assert "At Risk" in registry.class_labels


def test_risk_level_mapping_is_complete_and_correct():
    assert risk_level_from_category("At Risk") == "HIGH"
    assert risk_level_from_category("Average") == "MEDIUM"
    assert risk_level_from_category("Good") == "LOW"
    assert risk_level_from_category("Excellent") == "LOW"


def test_predict_for_student_returns_valid_shape():
    result = predict_for_student(SAMPLE_FEATURES)

    clf = result["classification"]
    assert clf["predicted_category"] in ("At Risk", "Average", "Good", "Excellent")
    assert clf["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert 0.0 <= clf["confidence"] <= 1.0
    assert len(clf["explanation"]) == 11  # one contribution per feature

    reg = result["regression"]
    assert 0.0 <= reg["predicted_gpa"] <= 4.0
    assert len(reg["explanation"]) == 11


def test_predict_is_deterministic_for_same_input():
    result_1 = predict_for_student(SAMPLE_FEATURES)
    result_2 = predict_for_student(SAMPLE_FEATURES)
    assert result_1["classification"]["predicted_category"] == result_2["classification"]["predicted_category"]
    assert result_1["regression"]["predicted_gpa"] == result_2["regression"]["predicted_gpa"]


def test_worse_inputs_shift_prediction_toward_higher_risk():
    """Sanity check that the model responds sensibly to input direction —
    not a claim about real-world causation, just a regression-safety test."""
    strong_features = {**SAMPLE_FEATURES, "attendance_percentage": 98.0, "midterm_score": 95.0, "quiz_avg": 95.0}
    weak_features = {**SAMPLE_FEATURES, "attendance_percentage": 30.0, "midterm_score": 20.0, "quiz_avg": 20.0}

    strong_result = predict_for_student(strong_features)
    weak_result = predict_for_student(weak_features)

    assert strong_result["regression"]["predicted_gpa"] > weak_result["regression"]["predicted_gpa"]
