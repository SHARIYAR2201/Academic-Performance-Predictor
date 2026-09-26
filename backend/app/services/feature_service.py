"""Aggregates a student's real academic records into the exact feature vector
the ML pipeline expects (see ml/preprocessing/pipeline.ALL_FEATURES).

This is what makes predictions genuine: features are computed from actual
assessments/attendance/academic_records rows for the student's current
semester, not fabricated or hand-entered at prediction time.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.academic import Course, Enrollment, Semester, Student
from app.models.enums import AssessmentType, EnrollmentStatus
from app.models.performance import AcademicRecord, Assessment, Attendance

ASSESSMENT_FEATURE_MAP = {
    AssessmentType.quiz: "quiz_avg",
    AssessmentType.assignment: "assignment_avg",
    AssessmentType.midterm: "midterm_score",
    AssessmentType.project: "project_score",
    AssessmentType.lab: "lab_score",
}


def _latest_two_semester_gpas(db: Session, student_id: int) -> tuple[float, float]:
    """Returns (previous_gpa, previous_semester_gpa) from the two most recent
    semesters that have academic_records for this student. Falls back to a
    neutral 2.5 default (documented) when history is insufficient — this
    happens for first-semester students and is expected, not an error."""
    rows = (
        db.execute(
            select(Semester.start_date, func.avg(AcademicRecord.grade_point))
            .join(AcademicRecord, AcademicRecord.semester_id == Semester.id)
            .where(AcademicRecord.student_id == student_id)
            .group_by(Semester.id, Semester.start_date)
            .order_by(Semester.start_date.desc())
            .limit(2)
        )
    ).all()

    if len(rows) == 0:
        return 2.5, 2.5
    if len(rows) == 1:
        gpa = float(rows[0][1])
        return gpa, gpa
    return float(rows[0][1]), float(rows[1][1])


def _current_semester_id(db: Session, student_id: int) -> int | None:
    """The student's most recent semester with an active enrollment."""
    return db.scalar(
        select(Enrollment.semester_id)
        .join(Semester, Semester.id == Enrollment.semester_id)
        .where(Enrollment.student_id == student_id, Enrollment.enrollment_status == EnrollmentStatus.active)
        .order_by(Semester.start_date.desc())
        .limit(1)
    )


def get_student_feature_vector(db: Session, student_id: int) -> dict:
    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Student not found.", code="student_not_found")

    previous_gpa, previous_semester_gpa = _latest_two_semester_gpas(db, student_id)
    trend_delta = previous_gpa - previous_semester_gpa
    historical_trend = 1 if trend_delta > 0.05 else (-1 if trend_delta < -0.05 else 0)

    semester_id = _current_semester_id(db, student_id)

    enrollment_ids: list[int] = []
    credit_load = 0.0
    if semester_id is not None:
        enrollment_rows = db.execute(
            select(Enrollment.id, Course.credit)
            .join(Course, Course.id == Enrollment.course_id)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.semester_id == semester_id,
                Enrollment.enrollment_status == EnrollmentStatus.active,
            )
        ).all()
        enrollment_ids = [r[0] for r in enrollment_rows]
        credit_load = float(sum(r[1] for r in enrollment_rows))

    # Attendance: average attendance_percentage across current enrollments.
    attendance_percentage = 75.0  # documented neutral default when no data yet
    if enrollment_ids:
        avg_attendance = db.scalar(
            select(func.avg(Attendance.attendance_percentage)).where(Attendance.enrollment_id.in_(enrollment_ids))
        )
        if avg_attendance is not None:
            attendance_percentage = float(avg_attendance)

    # Per-assessment-type averages (normalized to a 0-100 scale), across current enrollments.
    assessment_features = {feature_name: 70.0 for feature_name in ASSESSMENT_FEATURE_MAP.values()}  # neutral default
    if enrollment_ids:
        rows = db.execute(
            select(Assessment.assessment_type, func.avg(Assessment.score / Assessment.maximum_score * 100))
            .where(Assessment.enrollment_id.in_(enrollment_ids))
            .group_by(Assessment.assessment_type)
        ).all()
        for assessment_type, avg_pct in rows:
            feature_name = ASSESSMENT_FEATURE_MAP[assessment_type]
            assessment_features[feature_name] = float(avg_pct)

    completed_courses = db.scalar(
        select(func.count(Enrollment.id)).where(
            Enrollment.student_id == student_id, Enrollment.enrollment_status == EnrollmentStatus.completed
        )
    ) or 0

    return {
        "previous_gpa": previous_gpa,
        "previous_semester_gpa": previous_semester_gpa,
        "attendance_percentage": attendance_percentage,
        "quiz_avg": assessment_features["quiz_avg"],
        "assignment_avg": assessment_features["assignment_avg"],
        "midterm_score": assessment_features["midterm_score"],
        "project_score": assessment_features["project_score"],
        "lab_score": assessment_features["lab_score"],
        "completed_courses": int(completed_courses),
        "credit_load": credit_load if credit_load > 0 else 15.0,  # neutral default
        "historical_trend": historical_trend,
    }
