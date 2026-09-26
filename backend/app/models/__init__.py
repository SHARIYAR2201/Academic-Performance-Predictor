from app.db.base_class import Base  # noqa: F401
from app.models.academic import (  # noqa: F401
    Course,
    CourseInstructor,
    Department,
    Enrollment,
    Instructor,
    Semester,
    Student,
)
from app.models.audit import AuditLog  # noqa: F401
from app.models.ml import Dataset, MLModel, Prediction, PredictionExplanation  # noqa: F401
from app.models.performance import AcademicRecord, Assessment, Attendance  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Department",
    "Student",
    "Instructor",
    "Course",
    "Semester",
    "CourseInstructor",
    "Enrollment",
    "Assessment",
    "Attendance",
    "AcademicRecord",
    "Dataset",
    "MLModel",
    "Prediction",
    "PredictionExplanation",
    "AuditLog",
]
