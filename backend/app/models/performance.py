from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.enums import AssessmentType


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False)
    assessment_type: Mapped[AssessmentType] = mapped_column(Enum(AssessmentType, name="assessment_type"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    maximum_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("score >= 0", name="ck_assessments_score_non_negative"),
        CheckConstraint("maximum_score > 0", name="ck_assessments_max_score_positive"),
        CheckConstraint("score <= maximum_score", name="ck_assessments_score_le_max"),
        Index("idx_assessments_enrollment", "enrollment_id"),
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    total_classes: Mapped[int] = mapped_column(Integer, nullable=False)
    attended_classes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Generated column: always consistent with attended/total, never written directly.
    attendance_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        Computed(
            "CASE WHEN total_classes = 0 THEN 0 "
            "ELSE ROUND((attended_classes::NUMERIC / total_classes) * 100, 2) END",
            persisted=True,
        ),
    )

    __table_args__ = (
        CheckConstraint("total_classes >= 0", name="ck_attendance_total_non_negative"),
        CheckConstraint("attended_classes >= 0", name="ck_attendance_attended_non_negative"),
        CheckConstraint("attended_classes <= total_classes", name="ck_attendance_attended_le_total"),
    )


class AcademicRecord(Base):
    __tablename__ = "academic_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    grade: Mapped[str] = mapped_column(String(4), nullable=False)
    grade_point: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    gpa: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "semester_id", "course_id", name="uq_academic_record_student_semester_course"),
        CheckConstraint("grade_point BETWEEN 0 AND 4.0", name="ck_academic_records_grade_point_range"),
        CheckConstraint("gpa IS NULL OR gpa BETWEEN 0 AND 4.0", name="ck_academic_records_gpa_range"),
        Index("idx_academic_records_student", "student_id"),
    )
