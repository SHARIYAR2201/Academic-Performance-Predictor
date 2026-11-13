"""Cached loaders for the registry metadata and synthetic dataset."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = REPO_ROOT / "ml" / "inference" / "registry"
DATASET_PATH = REPO_ROOT / "data" / "synthetic" / "students_synthetic_v1.csv"


@st.cache_data
def load_metrics() -> dict:
    return json.loads((REGISTRY_DIR / "metrics.json").read_text(encoding="utf-8"))


@st.cache_data
def load_production() -> dict:
    return json.loads((REGISTRY_DIR / "production.json").read_text(encoding="utf-8"))


@st.cache_data
def load_dataset() -> pd.DataFrame:
    return pd.read_csv(DATASET_PATH)
