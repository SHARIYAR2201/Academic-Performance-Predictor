from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RiskLevel


class FeatureContribution(BaseModel):
    feature: str
    contribution: float
    direction: str


class ClassificationPredictionOut(BaseModel):
    predicted_category: str
    risk_level: RiskLevel
    confidence: float
    model_version: str
    explanation: list[FeatureContribution]


class RegressionPredictionOut(BaseModel):
    predicted_gpa: float
    model_version: str
    explanation: list[FeatureContribution]


class PredictionResponse(BaseModel):
    student_id: int
    generated_at: datetime
    classification: ClassificationPredictionOut
    regression: RegressionPredictionOut
    disclaimer: str = (
        "This prediction is a model-generated estimate based on historical and current "
        "academic data. It is not a certainty and must not be the sole basis for academic, "
        "disciplinary, or admissions decisions. Feature contributions describe the model's "
        "behavior, not proven real-world causes."
    )
