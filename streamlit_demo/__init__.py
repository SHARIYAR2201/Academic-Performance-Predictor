"""Standalone Streamlit demo for the academic performance predictor.

The demo reuses the trained artifacts in ``ml/inference/registry`` and the
backend's inference service. It deliberately does not include authentication,
RBAC, a database, or persisted predictions — those belong to the full
FastAPI + PostgreSQL + Next.js application.
"""
