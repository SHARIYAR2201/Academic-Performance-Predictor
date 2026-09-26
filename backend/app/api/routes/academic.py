from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.academic import (
    AssessmentCreate,
    AssessmentOut,
    AssignInstructorRequest,
    AttendanceOut,
    AttendanceUpsert,
    CourseCreate,
    CourseOut,
    DepartmentCreate,
    DepartmentOut,
    EnrollmentCreate,
    EnrollmentOut,
    InstructorProfileCreate,
    InstructorProfileOut,
    SemesterCreate,
    SemesterOut,
    StudentProfileCreate,
    StudentProfileOut,
)
from app.services import academic_service

router = APIRouter(tags=["academic"])

ADMIN_ONLY = require_roles(UserRole.admin, UserRole.super_admin)
INSTRUCTOR_OR_ADMIN = require_roles(UserRole.instructor, UserRole.admin, UserRole.super_admin)


# --- Departments ---
@router.post("/departments", response_model=DepartmentOut, status_code=201, dependencies=[Depends(ADMIN_ONLY)])
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)) -> DepartmentOut:
    return DepartmentOut.model_validate(academic_service.create_department(db, payload))


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)) -> list[DepartmentOut]:
    return [DepartmentOut.model_validate(d) for d in academic_service.list_departments(db)]


# --- Courses ---
@router.post("/courses", response_model=CourseOut, status_code=201, dependencies=[Depends(ADMIN_ONLY)])
def create_course(payload: CourseCreate, db: Session = Depends(get_db)) -> CourseOut:
    return CourseOut.model_validate(academic_service.create_course(db, payload))


@router.get("/courses", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)) -> list[CourseOut]:
    return [CourseOut.model_validate(c) for c in academic_service.list_courses(db)]


@router.post("/courses/{course_id}/instructors", status_code=201, dependencies=[Depends(ADMIN_ONLY)])
def assign_instructor(course_id: int, payload: AssignInstructorRequest, db: Session = Depends(get_db)) -> dict:
    assignment = academic_service.assign_instructor_to_course(db, course_id, payload)
    return {"id": assignment.id, "course_id": assignment.course_id, "instructor_id": assignment.instructor_id}


# --- Course roster (instructor-scoped) ---
@router.get("/courses/{course_id}/students")
def list_course_students(course_id: int, db: Session = Depends(get_db), current_user=Depends(INSTRUCTOR_OR_ADMIN)) -> list[dict]:
    return academic_service.list_students_for_course_instructor(db, current_user, course_id)


# --- Admin analytics ---
@router.get("/analytics/university", dependencies=[Depends(ADMIN_ONLY)])
def admin_analytics(db: Session = Depends(get_db)) -> dict:
    return academic_service.admin_analytics_summary(db)


# --- Semesters ---
@router.post("/semesters", response_model=SemesterOut, status_code=201, dependencies=[Depends(ADMIN_ONLY)])
def create_semester(payload: SemesterCreate, db: Session = Depends(get_db)) -> SemesterOut:
    return SemesterOut.model_validate(academic_service.create_semester(db, payload))


# --- Profile provisioning (admin links a user account to a role profile) ---
@router.post("/students", response_model=StudentProfileOut, status_code=201, dependencies=[Depends(ADMIN_ONLY)])
def create_student_profile(payload: StudentProfileCreate, db: Session = Depends(get_db)) -> StudentProfileOut:
    return StudentProfileOut.model_validate(academic_service.create_student_profile(db, payload))


@router.post("/instructors", response_model=InstructorProfileOut, status_code=201, dependencies=[Depends(ADMIN_ONLY)])
def create_instructor_profile(payload: InstructorProfileCreate, db: Session = Depends(get_db)) -> InstructorProfileOut:
    return InstructorProfileOut.model_validate(academic_service.create_instructor_profile(db, payload))


# --- Enrollments ---
@router.post("/enrollments", response_model=EnrollmentOut, status_code=201, dependencies=[Depends(ADMIN_ONLY)])
def create_enrollment(payload: EnrollmentCreate, db: Session = Depends(get_db)) -> EnrollmentOut:
    return EnrollmentOut.model_validate(academic_service.create_enrollment(db, payload))


# --- Assessments (instructor-entered, RBAC-scoped to their own courses) ---
@router.post("/assessments", response_model=AssessmentOut, status_code=201)
def record_assessment(payload: AssessmentCreate, db: Session = Depends(get_db), current_user=Depends(INSTRUCTOR_OR_ADMIN)) -> AssessmentOut:
    return AssessmentOut.model_validate(academic_service.record_assessment(db, current_user, payload))


# --- Attendance (instructor-entered, RBAC-scoped to their own courses) ---
@router.post("/attendance", response_model=AttendanceOut, status_code=201)
def upsert_attendance(payload: AttendanceUpsert, db: Session = Depends(get_db), current_user=Depends(INSTRUCTOR_OR_ADMIN)) -> AttendanceOut:
    return AttendanceOut.model_validate(academic_service.upsert_attendance(db, current_user, payload))
