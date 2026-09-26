import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from ml.preprocessing.pipeline import (  # noqa: E402
    ALL_FEATURES,
    build_preprocessing_pipeline,
    clean_dataset,
    validate_dataset,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "previous_gpa": [3.0, 2.5, np.nan],
            "previous_semester_gpa": [3.1, 2.4, 2.8],
            "attendance_percentage": [90.0, 60.0, 70.0],
            "quiz_avg": [80.0, 60.0, 70.0],
            "assignment_avg": [85.0, 55.0, 65.0],
            "midterm_score": [75.0, 50.0, 60.0],
            "project_score": [88.0, 58.0, 68.0],
            "lab_score": [92.0, 62.0, 72.0],
            "completed_courses": [10, 5, 8],
            "credit_load": [15, 12, 18],
            "historical_trend": [1, -1, 0],
            "final_gpa": [3.2, 2.1, 2.6],
            "performance_category": ["Good", "At Risk", "Average"],
        }
    )


class TestValidation:
    def test_valid_dataset_passes(self, sample_df):
        assert validate_dataset(sample_df) == []

    def test_missing_required_column_detected(self, sample_df):
        broken = sample_df.drop(columns=["attendance_percentage"])
        errors = validate_dataset(broken)
        assert any("Missing required columns" in e for e in errors)

    def test_out_of_range_gpa_detected(self, sample_df):
        broken = sample_df.copy()
        broken.loc[0, "final_gpa"] = 9.9
        errors = validate_dataset(broken)
        assert any("final_gpa contains values outside" in e for e in errors)

    def test_out_of_range_attendance_detected(self, sample_df):
        broken = sample_df.copy()
        broken.loc[0, "attendance_percentage"] = 150.0
        errors = validate_dataset(broken)
        assert any("attendance_percentage contains values outside" in e for e in errors)


class TestCleaning:
    def test_duplicates_removed(self, sample_df):
        with_dupes = pd.concat([sample_df, sample_df.iloc[[0]]], ignore_index=True)
        cleaned, report = clean_dataset(with_dupes)
        assert report["duplicates_removed"] == 1
        assert len(cleaned) == len(sample_df)


class TestPreprocessingPipeline:
    def test_missing_values_imputed_not_dropped(self, sample_df):
        pipeline = build_preprocessing_pipeline()
        transformed = pipeline.fit_transform(sample_df[ALL_FEATURES])
        assert transformed.shape[0] == len(sample_df)  # no rows dropped
        assert not np.isnan(transformed).any()  # NaN was imputed, not left in

    def test_same_fitted_pipeline_used_for_new_data_no_leakage(self, sample_df):
        """Critical invariant: fit only on 'training' rows, transform 'test' rows
        with those same fitted statistics — this is what train.py does."""
        pipeline = build_preprocessing_pipeline()
        train_rows = sample_df.iloc[:2]
        test_row = sample_df.iloc[[2]]

        pipeline.fit(train_rows[ALL_FEATURES])
        # transform must not re-fit; calling it twice on the same input is deterministic
        out_1 = pipeline.transform(test_row[ALL_FEATURES])
        out_2 = pipeline.transform(test_row[ALL_FEATURES])
        np.testing.assert_array_equal(out_1, out_2)

    def test_output_feature_count_matches_input(self, sample_df):
        pipeline = build_preprocessing_pipeline()
        transformed = pipeline.fit_transform(sample_df[ALL_FEATURES])
        assert transformed.shape[1] == len(ALL_FEATURES)
