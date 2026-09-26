from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.enums import DirectionType, PredictionType, RiskLevel
from app.models.ml import Prediction, PredictionExplanation
from app.schemas.prediction import (
    ClassificationPredictionOut,
    FeatureContribution,
    PredictionResponse,
    RegressionPredictionOut,
)
from app.services import feature_service, inference_service


def _persist_prediction(
    db: Session,
    student_id: int,
    prediction_type: PredictionType,
    model_version: str,
    predicted_value: float,
    risk_level: RiskLevel | None,
    confidence: float | None,
    explanation: list[dict],
) -> Prediction:
    prediction = Prediction(
        student_id=student_id,
        model_version=model_version,
        prediction_type=prediction_type,
        predicted_value=predicted_value,
        risk_level=risk_level,
        confidence=confidence,
    )
    db.add(prediction)
    db.flush()  # get prediction.id without committing yet

    for item in explanation:
        db.add(
            PredictionExplanation(
                prediction_id=prediction.id,
                feature=item["feature"],
                contribution=item["contribution"],
                direction=DirectionType(item["direction"]),
            )
        )
    return prediction


def generate_prediction_for_student(db: Session, student_id: int) -> PredictionResponse:
    features = feature_service.get_student_feature_vector(db, student_id)
    result = inference_service.predict_for_student(features)

    clf = result["classification"]
    reg = result["regression"]

    # Encode the classification's predicted category as a small ordinal for
    # `predicted_value` (numeric column) while the human-readable category
    # lives in the API response; risk_level is the DB's first-class signal.
    category_ordinal = {"At Risk": 0, "Average": 1, "Good": 2, "Excellent": 3}[clf["predicted_category"]]

    _persist_prediction(
        db,
        student_id=student_id,
        prediction_type=PredictionType.classification,
        model_version=clf["model_version"],
        predicted_value=category_ordinal,
        risk_level=RiskLevel(clf["risk_level"]),
        confidence=clf["confidence"],
        explanation=clf["explanation"],
    )
    _persist_prediction(
        db,
        student_id=student_id,
        prediction_type=PredictionType.gpa_regression,
        model_version=reg["model_version"],
        predicted_value=reg["predicted_gpa"],
        risk_level=None,
        confidence=None,
        explanation=reg["explanation"],
    )
    db.commit()

    return PredictionResponse(
        student_id=student_id,
        generated_at=datetime.now(UTC),
        classification=ClassificationPredictionOut(
            predicted_category=clf["predicted_category"],
            risk_level=RiskLevel(clf["risk_level"]),
            confidence=clf["confidence"],
            model_version=clf["model_version"],
            explanation=[FeatureContribution(**e) for e in clf["explanation"]],
        ),
        regression=RegressionPredictionOut(
            predicted_gpa=reg["predicted_gpa"],
            model_version=reg["model_version"],
            explanation=[FeatureContribution(**e) for e in reg["explanation"]],
        ),
    )
