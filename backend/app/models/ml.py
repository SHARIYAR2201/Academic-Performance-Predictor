from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.enums import DirectionType, PredictionType, PreprocessingStatus, RiskLevel


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    preprocessing_status: Mapped[PreprocessingStatus] = mapped_column(
        Enum(PreprocessingStatus, name="preprocessing_status"), nullable=False, default=PreprocessingStatus.pending
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_datasets_name_version"),
        CheckConstraint("row_count >= 0", name="ck_datasets_row_count_non_negative"),
    )


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[PredictionType] = mapped_column(Enum(PredictionType, name="prediction_type"), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    training_dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    is_production: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("name", "version", name="uq_ml_models_name_version"),)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    prediction_type: Mapped[PredictionType] = mapped_column(Enum(PredictionType, name="prediction_type"), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    risk_level: Mapped[RiskLevel | None] = mapped_column(Enum(RiskLevel, name="risk_level"), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 1", name="ck_predictions_confidence_range"),
        Index("idx_predictions_student_created", "student_id", "created_at"),
    )


class PredictionExplanation(Base):
    __tablename__ = "prediction_explanations"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False)
    feature: Mapped[str] = mapped_column(String(100), nullable=False)
    contribution: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    direction: Mapped[DirectionType] = mapped_column(Enum(DirectionType, name="direction_type"), nullable=False)

    __table_args__ = (Index("idx_explanations_prediction", "prediction_id"),)
