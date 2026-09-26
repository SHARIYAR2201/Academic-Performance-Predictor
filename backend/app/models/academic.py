from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import EnrollmentStatus


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    student_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    enrollment_year: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="student_profile")

    __table_args__ = (
        CheckConstraint("enrollment_year BETWEEN 2000 AND 2100", name="ck_students_enrollment_year_range"),
        Index("idx_students_department", "department_id"),
    )


class Instructor(Base):
    __tablename__ = "instructors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)

    user = relationship("User", back_populates="instructor_profile")

    __table_args__ = (Index("idx_instructors_department", "department_id"),)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    course_name: Mapped[str] = mapped_column(String(200), nullable=False)
    credit: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (
        CheckConstraint("credit > 0", name="ck_courses_credit_positive"),
        Index("idx_courses_department", "department_id"),
    )


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "year", name="uq_semesters_name_year"),
        CheckConstraint("end_date > start_date", name="ck_semesters_date_order"),
    )


class CourseInstructor(Base):
    """Join table driving instructor RBAC scoping: which instructor teaches which
    course in which semester. Authorization checks filter through this table."""

    __tablename__ = "course_instructors"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("instructors.id", ondelete="CASCADE"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("course_id", "instructor_id", "semester_id", name="uq_course_instructor_semester"),
    )


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False)
    enrollment_status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, name="enrollment_status"), nullable=False, default=EnrollmentStatus.active
    )

    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "semester_id", name="uq_enrollment_student_course_semester"),
        Index("idx_enrollments_student", "student_id"),
        Index("idx_enrollments_course", "course_id"),
    )
