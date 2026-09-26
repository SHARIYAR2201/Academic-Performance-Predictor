"""Manual smoke test for Phase 2: proves the ORM models round-trip correctly
against the real Postgres schema and that DB-level constraints are enforced.

Run with: .venv/bin/python scripts/smoke_test_models.py
"""
import sys
from datetime import date

from sqlalchemy.exc import IntegrityError

sys.path.insert(0, ".")

from app.db.session import SessionLocal
from app.models import (
    AcademicRecord,
    Assessment,
    Attendance,
    Course,
    Dataset,
    Department,
    Enrollment,
    Instructor,
    MLModel,
    Semester,
    Student,
    User,
)
from app.models.enums import (
    AssessmentType,
    EnrollmentStatus,
    PredictionType,
    PreprocessingStatus,
    UserRole,
)

db = SessionLocal()

try:
    # --- 1. Core entities ---
    dept = Department(name="Computer Science", code="CSE")
    db.add(dept)
    db.flush()

    student_user = User(
        name="Test Student", email="student1@test.edu", password_hash="hashed", role=UserRole.student
    )
    instructor_user = User(
        name="Test Instructor", email="instructor1@test.edu", password_hash="hashed", role=UserRole.instructor
    )
    db.add_all([student_user, instructor_user])
    db.flush()

    student = Student(user_id=student_user.id, student_id="CSE-2023-001", department_id=dept.id, enrollment_year=2023)
    instructor = Instructor(user_id=instructor_user.id, employee_id="EMP-001", department_id=dept.id)
    db.add_all([student, instructor])
    db.flush()

    course = Course(course_code="CSE401", course_name="Machine Learning", credit=3.0, department_id=dept.id)
    semester = Semester(name="Spring", year=2026, start_date=date(2026, 1, 1), end_date=date(2026, 5, 1))
    db.add_all([course, semester])
    db.flush()

    enrollment = Enrollment(
        student_id=student.id, course_id=course.id, semester_id=semester.id, enrollment_status=EnrollmentStatus.active
    )
    db.add(enrollment)
    db.flush()

    # --- 2. Assessment + attendance (test generated column + check constraints) ---
    assessment = Assessment(
        enrollment_id=enrollment.id,
        assessment_type=AssessmentType.midterm,
        score=78,
        maximum_score=100,
        assessment_date=date(2026, 3, 1),
    )
    attendance = Attendance(enrollment_id=enrollment.id, total_classes=40, attended_classes=36)
    db.add_all([assessment, attendance])
    db.flush()
    db.refresh(attendance)
    assert attendance.attendance_percentage == 90.00, f"generated column wrong: {attendance.attendance_percentage}"
    print("[OK] attendance_percentage generated column computed correctly:", attendance.attendance_percentage)

    # --- 3. Academic record ---
    record = AcademicRecord(
        student_id=student.id, semester_id=semester.id, course_id=course.id, grade="B+", grade_point=3.3, gpa=3.3
    )
    db.add(record)
    db.flush()
    print("[OK] academic_records insert succeeded")

    # --- 4. CHECK constraint enforcement: score > maximum_score must fail ---
    bad_assessment = Assessment(
        enrollment_id=enrollment.id,
        assessment_type=AssessmentType.quiz,
        score=999,
        maximum_score=10,
        assessment_date=date(2026, 3, 2),
    )
    db.add(bad_assessment)
    try:
        db.flush()
        raise AssertionError("Expected IntegrityError for score > maximum_score, but insert succeeded")
    except IntegrityError:
        db.rollback()
        print("[OK] CHECK constraint correctly rejected score > maximum_score")

    # --- 5. Partial unique index: only one production model per task_type ---
    dataset = Dataset(name="synthetic-v1", version="1.0", file_path="data/synthetic/v1.csv", row_count=1000)
    db.add(dataset)
    db.flush()

    model_a = MLModel(
        name="rf_classifier",
        version="1.0",
        algorithm="RandomForestClassifier",
        task_type=PredictionType.classification,
        metrics={"accuracy": 0.81, "f1": 0.77},
        training_dataset_id=dataset.id,
        is_production=True,
    )
    db.add(model_a)
    db.flush()
    print("[OK] first production classification model inserted")

    model_b = MLModel(
        name="xgb_classifier",
        version="1.0",
        algorithm="XGBClassifier",
        task_type=PredictionType.classification,
        metrics={"accuracy": 0.84, "f1": 0.80},
        training_dataset_id=dataset.id,
        is_production=True,  # should violate partial unique index
    )
    db.add(model_b)
    try:
        db.flush()
        raise AssertionError("Expected IntegrityError for second production model of same task_type")
    except IntegrityError:
        db.rollback()
        print("[OK] partial unique index correctly rejected a second production model for the same task_type")

    db.commit()
    print("\nALL SMOKE TESTS PASSED")

finally:
    db.close()
