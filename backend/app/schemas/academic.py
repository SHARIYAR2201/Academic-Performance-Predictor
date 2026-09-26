from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssessmentType, EnrollmentStatus


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str = Field(min_length=1, max_length=20)


class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class CourseCreate(BaseModel):
    course_code: str = Field(min_length=1, max_length=20)
    course_name: str = Field(min_length=1, max_length=200)
    credit: float = Field(gt=0)
    department_id: int


class CourseOut(BaseModel):
    id: int
    course_code: str
    course_name: str
    credit: float
    department_id: int

    model_config = ConfigDict(from_attributes=True)


class SemesterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    year: int
    start_date: date
    end_date: date


class SemesterOut(BaseModel):
    id: int
    name: str
    year: int
    start_date: date
    end_date: date

    model_config = ConfigDict(from_attributes=True)


class StudentProfileCreate(BaseModel):
    user_id: int
    student_id: str = Field(min_length=1, max_length=30)
    department_id: int
    enrollment_year: int = Field(ge=2000, le=2100)


class StudentProfileOut(BaseModel):
    id: int
    user_id: int
    student_id: str
    department_id: int
    enrollment_year: int

    model_config = ConfigDict(from_attributes=True)


class InstructorProfileCreate(BaseModel):
    user_id: int
    employee_id: str = Field(min_length=1, max_length=30)
    department_id: int


class InstructorProfileOut(BaseModel):
    id: int
    user_id: int
    employee_id: str
    department_id: int

    model_config = ConfigDict(from_attributes=True)


class AssignInstructorRequest(BaseModel):
    instructor_id: int
    semester_id: int


class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int
    semester_id: int


class EnrollmentOut(BaseModel):
    id: int
    student_id: int
    course_id: int
    semester_id: int
    enrollment_status: EnrollmentStatus

    model_config = ConfigDict(from_attributes=True)


class AssessmentCreate(BaseModel):
    enrollment_id: int
    assessment_type: AssessmentType
    score: float = Field(ge=0)
    maximum_score: float = Field(gt=0)
    assessment_date: date


class AssessmentOut(BaseModel):
    id: int
    enrollment_id: int
    assessment_type: AssessmentType
    score: float
    maximum_score: float
    assessment_date: date

    model_config = ConfigDict(from_attributes=True)


class AttendanceUpsert(BaseModel):
    enrollment_id: int
    total_classes: int = Field(ge=0)
    attended_classes: int = Field(ge=0)


class AttendanceOut(BaseModel):
    id: int
    enrollment_id: int
    total_classes: int
    attended_classes: int
    attendance_percentage: float

    model_config = ConfigDict(from_attributes=True)
