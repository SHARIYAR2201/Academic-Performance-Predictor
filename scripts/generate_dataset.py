"""Generates a SYNTHETIC academic performance dataset for local development
and model training.

*** THIS DATA IS NOT REAL. It is procedurally generated with documented,
approximate relationships between attendance/assessments and outcomes, plus
random noise. It must never be presented as real institutional data. ***

Usage:
    python scripts/generate_dataset.py --n 3000 --seed 42 --out data/synthetic/students_synthetic_v1.csv

Feature rationale (spec section 12 — only academically relevant variables):
    previous_gpa            - strongest predictor of future performance in
                               education-research literature; carried forward.
    previous_semester_gpa   - captures recent trend, not just historical average.
    attendance_percentage   - class attendance correlates with performance.
    quiz_avg / assignment_avg / midterm_score / project_score / lab_score
                             - direct, current-semester academic signal.
    completed_courses       - proxy for class standing / experience.
    credit_load              - workload pressure.
    historical_trend          - improving (+1) / stable (0) / declining (-1)
                               trajectory over the last two semesters.
No demographic, protected, or non-academic attributes are used.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    previous_gpa = np.clip(rng.normal(3.0, 0.55, n), 0.0, 4.0)
    historical_trend = rng.choice([-1, 0, 1], size=n, p=[0.25, 0.45, 0.30])
    previous_semester_gpa = np.clip(previous_gpa + historical_trend * rng.uniform(0.05, 0.35, n), 0.0, 4.0)

    # Attendance correlates with GPA but has its own independent noise.
    attendance_percentage = np.clip(60 + previous_gpa * 10 + rng.normal(0, 12, n), 0, 100)

    # Current-semester assessment signals, each anchored to previous_gpa +
    # attendance with independent noise so no single feature is a proxy label.
    base_ability = 0.55 * previous_gpa / 4.0 + 0.25 * attendance_percentage / 100 + 0.20 * rng.uniform(0, 1, n)
    quiz_avg = np.clip(base_ability * 100 + rng.normal(0, 8, n), 0, 100)
    assignment_avg = np.clip(base_ability * 100 + rng.normal(0, 7, n), 0, 100)
    midterm_score = np.clip(base_ability * 100 + rng.normal(0, 10, n), 0, 100)
    project_score = np.clip(base_ability * 100 + rng.normal(0, 9, n), 0, 100)
    lab_score = np.clip(base_ability * 100 + rng.normal(0, 6, n), 0, 100)

    completed_courses = rng.integers(0, 40, n)
    credit_load = rng.integers(9, 19, n)

    # Final GPA: weighted combination of the above + irreducible noise —
    # deliberately imperfect so models cannot achieve unrealistic accuracy.
    final_gpa = (
        0.35 * previous_gpa
        + 0.15 * previous_semester_gpa
        + 0.15 * (attendance_percentage / 100) * 4.0
        + 0.10 * (quiz_avg / 100) * 4.0
        + 0.10 * (assignment_avg / 100) * 4.0
        + 0.08 * (midterm_score / 100) * 4.0
        + 0.05 * (project_score / 100) * 4.0
        + 0.02 * (lab_score / 100) * 4.0
        - 0.01 * np.clip(credit_load - 15, 0, None)  # heavy overload has a small penalty
        + rng.normal(0, 0.25, n)  # irreducible noise
    )
    final_gpa = np.clip(final_gpa, 0.0, 4.0).round(2)

    df = pd.DataFrame(
        {
            "previous_gpa": previous_gpa.round(2),
            "previous_semester_gpa": previous_semester_gpa.round(2),
            "attendance_percentage": attendance_percentage.round(2),
            "quiz_avg": quiz_avg.round(2),
            "assignment_avg": assignment_avg.round(2),
            "midterm_score": midterm_score.round(2),
            "project_score": project_score.round(2),
            "lab_score": lab_score.round(2),
            "completed_courses": completed_courses,
            "credit_load": credit_load,
            "historical_trend": historical_trend,
            "final_gpa": final_gpa,
        }
    )

    # Derived classification target (spec section 9, Task A) using documented,
    # configurable thresholds — not claimed as objective academic truth.
    def classify(gpa: float) -> str:
        if gpa >= 3.5:
            return "Excellent"
        if gpa >= 3.0:
            return "Good"
        if gpa >= 2.3:
            return "Average"
        return "At Risk"

    df["performance_category"] = df["final_gpa"].apply(classify)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=3000, help="Number of synthetic student records")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out", type=str, default="data/synthetic/students_synthetic_v1.csv")
    args = parser.parse_args()

    df = generate(args.n, args.seed)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"Generated {len(df)} SYNTHETIC records -> {out_path}")
    print("\nClass balance (performance_category):")
    print(df["performance_category"].value_counts())
    print(f"\nfinal_gpa: mean={df['final_gpa'].mean():.2f} std={df['final_gpa'].std():.2f}")


if __name__ == "__main__":
    main()
