"""Registers the dataset and production models from ml/inference/registry/
into the ml_models / datasets tables — completing spec step 12 ("Register
model") of the training pipeline.

Usage:
    python ml/training/register_models.py --db-url postgresql://postgres:postgres@localhost:5432/academic_predictor
"""
import argparse
import json
from pathlib import Path

import psycopg2
from psycopg2.extras import Json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", type=str, required=True)
    parser.add_argument("--registry", type=str, default="ml/inference/registry")
    parser.add_argument("--dataset-path", type=str, default="data/synthetic/students_synthetic_v1.csv")
    args = parser.parse_args()

    registry_dir = Path(args.registry)
    metrics = json.loads((registry_dir / "metrics.json").read_text())
    production = json.loads((registry_dir / "production.json").read_text())

    conn = psycopg2.connect(args.db_url)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            row_count = sum(1 for _ in open(args.dataset_path)) - 1  # minus header

            cur.execute(
                "INSERT INTO datasets (name, version, file_path, row_count, preprocessing_status) "
                "VALUES (%s, %s, %s, %s, 'processed') "
                "ON CONFLICT (name, version) DO UPDATE SET row_count = EXCLUDED.row_count "
                "RETURNING id",
                ("students_synthetic", metrics["dataset_version"], args.dataset_path, row_count),
            )
            dataset_id = cur.fetchone()[0]

            clf_name = production["classification_model_file"].removeprefix("classification_").removesuffix(".joblib")
            reg_name = production["regression_model_file"].removeprefix("regression_").removesuffix(".joblib")

            # Unset any prior production flag for each task before inserting the new one
            # (mirrors what an admin "promote to production" action would do).
            cur.execute("UPDATE ml_models SET is_production = FALSE WHERE task_type = 'classification'")
            cur.execute("UPDATE ml_models SET is_production = FALSE WHERE task_type = 'gpa_regression'")

            cur.execute(
                "INSERT INTO ml_models (name, version, algorithm, task_type, metrics, training_dataset_id, is_production) "
                "VALUES (%s, %s, %s, 'classification', %s, %s, TRUE) "
                "ON CONFLICT (name, version) DO UPDATE SET is_production = TRUE, metrics = EXCLUDED.metrics",
                (
                    clf_name,
                    metrics["dataset_version"],
                    clf_name,
                    Json(metrics["classification"][clf_name]),
                    dataset_id,
                ),
            )
            cur.execute(
                "INSERT INTO ml_models (name, version, algorithm, task_type, metrics, training_dataset_id, is_production) "
                "VALUES (%s, %s, %s, 'gpa_regression', %s, %s, TRUE) "
                "ON CONFLICT (name, version) DO UPDATE SET is_production = TRUE, metrics = EXCLUDED.metrics",
                (
                    reg_name,
                    metrics["dataset_version"],
                    reg_name,
                    Json(metrics["regression"][reg_name]),
                    dataset_id,
                ),
            )
        conn.commit()
        print(f"Registered dataset id={dataset_id}, classification={clf_name}, regression={reg_name}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
