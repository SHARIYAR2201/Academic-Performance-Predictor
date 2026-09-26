import enum


class UserRole(str, enum.Enum):
    student = "student"
    instructor = "instructor"
    admin = "admin"
    super_admin = "super_admin"


class EnrollmentStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    dropped = "dropped"
    withdrawn = "withdrawn"


class AssessmentType(str, enum.Enum):
    quiz = "quiz"
    assignment = "assignment"
    midterm = "midterm"
    final = "final"
    project = "project"
    lab = "lab"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PredictionType(str, enum.Enum):
    classification = "classification"
    gpa_regression = "gpa_regression"


class PreprocessingStatus(str, enum.Enum):
    pending = "pending"
    validated = "validated"
    failed = "failed"
    processed = "processed"


class DirectionType(str, enum.Enum):
    positive = "positive"
    negative = "negative"
