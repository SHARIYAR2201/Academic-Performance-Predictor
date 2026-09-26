from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models.academic import Course, CourseInstructor, Department, Enrollment, Instructor, Semester, Student
from app.models.performance import Assessment, Attendance
from app.models.user import User
from app.models.user import User as UserModel
from app.schemas.academic import (
    AssessmentCreate,
    AssignInstructorRequest,
    AttendanceUpsert,
    CourseCreate,
    DepartmentCreate,
    EnrollmentCreate,
    InstructorProfileCreate,
    SemesterCreate,
    StudentProfileCreate,
)


def list_students_for_course_instructor(db: Session, current_user: User, course_id: int) -> list[dict]:
    """Instructor's own roster for a course they teach (any semester);
    admins can view any course's roster. Spec section 2.2 scoping."""
    if current_user.role.value not in ("admin", "super_admin"):
        if current_user.role.value != "instructor":
            raise ForbiddenError("Only instructors and admins may view course rosters.", code="role_not_permitted")
        instructor = db.scalar(select(Instructor).where(Instructor.user_id == current_user.id))
        owns_course = instructor and db.scalar(
            select(CourseInstructor).where(
                CourseInstructor.instructor_id == instructor.id, CourseInstructor.course_id == course_id
            )
        )
        if not owns_course:
            raise ForbiddenError("You are not assigned to this course.", code="not_assigned_instructor")

    rows = db.execute(
        select(Student.id, Student.student_id, Enrollment.id)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .where(Enrollment.course_id == course_id)
    ).all()
    return [{"student_profile_id": r[0], "student_id": r[1], "enrollment_id": r[2]} for r in rows]


def admin_analytics_summary(db: Session) -> dict:
    from app.models.ml import MLModel
    from app.models.performance import AcademicRecord

    total_students = db.scalar(select(func.count(Student.id))) or 0
    total_instructors = db.scalar(select(func.count(Instructor.id))) or 0
    total_courses = db.scalar(select(func.count(Course.id))) or 0
    avg_gpa = db.scalar(select(func.avg(AcademicRecord.grade_point)))
    avg_attendance = db.scalar(select(func.avg(Attendance.attendance_percentage)))
    production_models = list(
        db.execute(select(MLModel.name, MLModel.version, MLModel.task_type).where(MLModel.is_production.is_(True)))
    )

    return {
        "total_students": total_students,
        "total_instructors": total_instructors,
        "total_courses": total_courses,
        "average_gpa": round(float(avg_gpa), 2) if avg_gpa is not None else None,
        "average_attendance_percentage": round(float(avg_attendance), 2) if avg_attendance is not None else None,
        "production_models": [{"name": r[0], "version": r[1], "task_type": r[2].value} for r in production_models],
    }


def assert_user_can_access_student(db: Session, current_user: User, student_id: int) -> Student:
    """Authorization for reading a specific student's data/predictions:
    - student: only themselves
    - instructor: only students currently enrolled in a course they teach
    - admin/super_admin: any student
    """
    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Student not found.", code="student_not_found")

    if current_user.role.value in ("admin", "super_admin"):
        return student

    if current_user.role.value == "student":
        if student.user_id != current_user.id:
            raise ForbiddenError("Students can only access their own data.", code="not_self")
        return student

    if current_user.role.value == "instructor":
        instructor = db.scalar(select(Instructor).where(Instructor.user_id == current_user.id))
        if instructor is None:
            raise ForbiddenError("No instructor profile found for this account.", code="no_instructor_profile")

        shares_a_course = db.scalar(
            select(Enrollment)
            .join(CourseInstructor, CourseInstructor.course_id == Enrollment.course_id)
            .where(
                Enrollment.student_id == student_id,
                CourseInstructor.instructor_id == instructor.id,
                CourseInstructor.semester_id == Enrollment.semester_id,
            )
        )
        if shares_a_course is None:
            raise ForbiddenError(
                "You are not the assigned instructor for any of this student's courses.", code="not_assigned_instructor"
            )
        return student

    raise ForbiddenError("Role not permitted.", code="role_not_permitted")


# ---------------------------------------------------------------------------
# Profile provisioning (admin links an existing user account to a role profile)
# ---------------------------------------------------------------------------
def create_student_profile(db: Session, payload: StudentProfileCreate) -> Student:
    user = db.get(UserModel, payload.user_id)
    if user is None:
        raise NotFoundError("User not found.", code="user_not_found")
    if user.role.value != "student":
        raise ConflictError("User does not have the student role.", code="wrong_role")
    if not db.get(Department, payload.department_id):
        raise NotFoundError("Department not found.", code="department_not_found")
    if db.scalar(select(Student).where(Student.user_id == payload.user_id)):
        raise ConflictError("This user already has a student profile.", code="profile_exists")

    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def create_instructor_profile(db: Session, payload: InstructorProfileCreate) -> Instructor:
    user = db.get(UserModel, payload.user_id)
    if user is None:
        raise NotFoundError("User not found.", code="user_not_found")
    if user.role.value != "instructor":
        raise ConflictError("User does not have the instructor role.", code="wrong_role")
    if not db.get(Department, payload.department_id):
        raise NotFoundError("Department not found.", code="department_not_found")
    if db.scalar(select(Instructor).where(Instructor.user_id == payload.user_id)):
        raise ConflictError("This user already has an instructor profile.", code="profile_exists")

    instructor = Instructor(**payload.model_dump())
    db.add(instructor)
    db.commit()
    db.refresh(instructor)
    return instructor


# ---------------------------------------------------------------------------
# Reference data (admin-managed)
# ---------------------------------------------------------------------------
def create_department(db: Session, payload: DepartmentCreate) -> Department:
    if db.scalar(select(Department).where(Department.code == payload.code)):
        raise ConflictError("A department with this code already exists.", code="department_code_taken")
    dept = Department(**payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


def list_departments(db: Session) -> list[Department]:
    return list(db.scalars(select(Department)))


def create_course(db: Session, payload: CourseCreate) -> Course:
    if not db.get(Department, payload.department_id):
        raise NotFoundError("Department not found.", code="department_not_found")
    if db.scalar(select(Course).where(Course.course_code == payload.course_code)):
        raise ConflictError("A course with this code already exists.", code="course_code_taken")
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def list_courses(db: Session) -> list[Course]:
    return list(db.scalars(select(Course)))


def create_semester(db: Session, payload: SemesterCreate) -> Semester:
    semester = Semester(**payload.model_dump())
    db.add(semester)
    db.commit()
    db.refresh(semester)
    return semester


def assign_instructor_to_course(db: Session, course_id: int, payload: AssignInstructorRequest) -> CourseInstructor:
    if not db.get(Course, course_id):
        raise NotFoundError("Course not found.", code="course_not_found")
    if not db.get(Instructor, payload.instructor_id):
        raise NotFoundError("Instructor not found.", code="instructor_not_found")
    if not db.get(Semester, payload.semester_id):
        raise NotFoundError("Semester not found.", code="semester_not_found")

    existing = db.scalar(
        select(CourseInstructor).where(
            CourseInstructor.course_id == course_id,
            CourseInstructor.instructor_id == payload.instructor_id,
            CourseInstructor.semester_id == payload.semester_id,
        )
    )
    if existing:
        raise ConflictError("This instructor is already assigned to this course/semester.", code="assignment_exists")

    assignment = CourseInstructor(course_id=course_id, instructor_id=payload.instructor_id, semester_id=payload.semester_id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------
def create_enrollment(db: Session, payload: EnrollmentCreate) -> Enrollment:
    existing = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == payload.student_id,
            Enrollment.course_id == payload.course_id,
            Enrollment.semester_id == payload.semester_id,
        )
    )
    if existing:
        raise ConflictError("Student is already enrolled in this course for this semester.", code="already_enrolled")

    enrollment = Enrollment(**payload.model_dump())
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def _instructor_owns_enrollment(db: Session, instructor: Instructor, enrollment: Enrollment) -> bool:
    return (
        db.scalar(
            select(CourseInstructor).where(
                CourseInstructor.instructor_id == instructor.id,
                CourseInstructor.course_id == enrollment.course_id,
                CourseInstructor.semester_id == enrollment.semester_id,
            )
        )
        is not None
    )


def _get_enrollment_scoped_for_write(db: Session, current_user: User, enrollment_id: int) -> Enrollment:
    """Fetches an enrollment, enforcing that only admins or the instructor
    actually assigned to that course/semester may write assessment/attendance
    data for it (spec section 2.2: "Instructors must only access students/
    courses they are authorized to access.")."""
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise NotFoundError("Enrollment not found.", code="enrollment_not_found")

    if current_user.role.value in ("admin", "super_admin"):
        return enrollment

    if current_user.role.value == "instructor":
        instructor = db.scalar(select(Instructor).where(Instructor.user_id == current_user.id))
        if instructor is None or not _instructor_owns_enrollment(db, instructor, enrollment):
            raise ForbiddenError(
                "You are not the assigned instructor for this course/semester.", code="not_assigned_instructor"
            )
        return enrollment

    raise ForbiddenError("Only instructors and admins may enter academic data.", code="role_not_permitted")


# ---------------------------------------------------------------------------
# Assessments / Attendance (instructor-entered, RBAC-scoped)
# ---------------------------------------------------------------------------
def record_assessment(db: Session, current_user: User, payload: AssessmentCreate) -> Assessment:
    _get_enrollment_scoped_for_write(db, current_user, payload.enrollment_id)
    assessment = Assessment(**payload.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def upsert_attendance(db: Session, current_user: User, payload: AttendanceUpsert) -> Attendance:
    _get_enrollment_scoped_for_write(db, current_user, payload.enrollment_id)

    record = db.scalar(select(Attendance).where(Attendance.enrollment_id == payload.enrollment_id))
    if record is None:
        record = Attendance(
            enrollment_id=payload.enrollment_id,
            total_classes=payload.total_classes,
            attended_classes=payload.attended_classes,
        )
        db.add(record)
    else:
        record.total_classes = payload.total_classes
        record.attended_classes = payload.attended_classes

    db.commit()
    db.refresh(record)
    return record
