from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.academic import router as academic_router
from app.api.routes.auth import router as auth_router
from app.api.routes.predictions import router as predictions_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.ENVIRONMENT)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "Academic analytics platform with ML-based performance prediction and an "
        "early-warning system. All predictions are model-generated estimates, not "
        "guarantees — see /docs and docs/machine-learning.md."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


register_exception_handlers(app)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(academic_router, prefix=settings.API_V1_PREFIX)
app.include_router(predictions_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
