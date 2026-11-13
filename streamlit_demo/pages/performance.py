"""Model-performance page: real held-out metrics from the training run."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from streamlit_demo.data import load_metrics, load_production
from streamlit_demo.ui import confusion_matrix_chart


def _highlight_selected(row: pd.Series, selected: str) -> list[str]:
    style = "background-color: #dcfce7; font-weight: 600" if row["Model"] == selected else ""
    return [style] * len(row)


def render() -> None:
    st.title("Model performance")
    st.markdown(
        "These are the real held-out metrics produced by `ml/training/train.py`. "
        "The production models are selected by **macro-F1** (classification) and **R²** "
        "(regression) rather than raw accuracy, so the minority *At Risk* class is not ignored."
    )

    metrics = load_metrics()
    production = load_production()
    selected_classifier = metrics["selected_production"]["classification"]
    selected_regressor = metrics["selected_production"]["regression"]

    left, middle, right = st.columns(3)
    left.metric("Production classifier", selected_classifier)
    middle.metric("Production regressor", selected_regressor)
    right.metric(
        "Dataset",
        f"{metrics['dataset_rows']:,} rows",
        help=f"Synthetic dataset version {metrics['dataset_version']}",
    )

    st.warning(
        "The training data is **synthetic**. These metrics describe performance on that generated "
        "dataset only — they are not evidence of real-world predictive accuracy."
    )

    st.subheader("Classification comparison")
    classification_rows = []
    for name, model_metrics in metrics["classification"].items():
        classification_rows.append(
            {
                "Model": name,
                "Accuracy": model_metrics["accuracy"],
                "Macro F1": model_metrics["f1_macro"],
                "Macro precision": model_metrics["precision_macro"],
                "Macro recall": model_metrics["recall_macro"],
                "ROC-AUC (OVR)": model_metrics["roc_auc_ovr_macro"],
            }
        )
    classification_frame = (
        pd.DataFrame(classification_rows).sort_values("Macro F1", ascending=False).reset_index(drop=True)
    )
    st.dataframe(
        classification_frame.style.apply(_highlight_selected, selected=selected_classifier, axis=1),
        hide_index=True,
        width="stretch",
    )
    st.caption("Green row = selected for production. Macro-F1 weights every category equally.")

    st.subheader("Regression comparison")
    regression_rows = []
    for name, model_metrics in metrics["regression"].items():
        regression_rows.append(
            {
                "Model": name,
                "R²": model_metrics["r2"],
                "MAE": model_metrics["mae"],
                "RMSE": model_metrics["rmse"],
            }
        )
    regression_frame = pd.DataFrame(regression_rows).sort_values("R²", ascending=False).reset_index(drop=True)
    st.dataframe(
        regression_frame.style.apply(_highlight_selected, selected=selected_regressor, axis=1),
        hide_index=True,
        width="stretch",
    )
    st.caption("Green row = selected for production. R² is the primary criterion.")

    st.subheader("Production classifier confusion matrix")
    production_metrics = metrics["classification"][selected_classifier]
    st.altair_chart(
        confusion_matrix_chart(production_metrics["confusion_matrix"], production_metrics["class_labels"]),
        width="stretch",
    )
    st.caption("Held-out test set (20% of the synthetic dataset). Rows are actual categories, columns are predictions.")

    st.subheader("Published artifacts")
    st.code(
        "\n".join(
            [
                f"classification: {production['classification_model_file']}",
                f"regression:     {production['regression_model_file']}",
                f"feature order:  {', '.join(production['feature_order'])}",
            ]
        ),
        language="text",
    )
    st.caption(
        "Model promotion is file-based via `ml/inference/registry/production.json`. "
        "The Streamlit demo loads these artifacts directly at startup."
    )
