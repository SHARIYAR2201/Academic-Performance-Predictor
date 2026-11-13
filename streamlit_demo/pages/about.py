"""About page: what this demo is (and is not)."""
from __future__ import annotations

import streamlit as st


def render() -> None:
    st.title("About this demo")

    st.markdown(
        """
This is the **Streamlit ML demo** for the Intelligent Academic Performance Prediction &
Early-Warning System. It loads the trained model artifacts directly from
`ml/inference/registry/` and reuses the backend's real inference + SHAP code.

The full project remains a three-tier application:

```text
Next.js frontend  ->  FastAPI REST API  ->  PostgreSQL 16
                            |
                            +-> trained scikit-learn artifacts (joblib)
```

### What the demo includes

- Real production models: logistic regression (performance category) and
  linear regression (predicted GPA)
- The same preprocessing pipeline used at training time
- LOW / MEDIUM / HIGH early-warning risk levels
- SHAP feature contributions for both tasks
- Real held-out model-comparison metrics
- An explorer for the synthetic training dataset
"""
    )

    st.subheader("What this demo deliberately omits")
    st.markdown(
        """
- Login, JWT auth, and role-based access control
- Student/instructor/admin records and dashboards
- PostgreSQL persistence and the audit trail
- Saved prediction history

Those features live in the FastAPI + PostgreSQL + Next.js application. This
Streamlit app is a public, read-only demonstration of the machine-learning
layer — it never reads or writes student records.
"""
    )

    st.subheader("Run locally")
    st.code(
        "pip install -r requirements.txt\nstreamlit run streamlit_app.py",
        language="powershell",
    )
    st.caption(
        "Use Python 3.12 if possible. The ML package versions in the root "
        "`requirements.txt` match the versions used to train the committed artifacts."
    )

    st.subheader("Important limitation")
    st.error(
        "The training dataset is entirely synthetic and every prediction is a model-generated "
        "estimate. This system must not be used as the sole basis for grading, disciplinary, or "
        "admissions decisions."
    )

    st.subheader("Source")
    st.markdown(
        "- [GitHub repository](https://github.com/SHARIYAR2201/Academic-Performance-Predictor)\n"
        "- [Architecture](https://github.com/SHARIYAR2201/Academic-Performance-Predictor/blob/main/docs/architecture.md)\n"
        "- [Model evaluation](https://github.com/SHARIYAR2201/Academic-Performance-Predictor/blob/main/docs/model-evaluation.md)\n"
        "- [Deployment notes](https://github.com/SHARIYAR2201/Academic-Performance-Predictor/blob/main/docs/deployment.md)"
    )
