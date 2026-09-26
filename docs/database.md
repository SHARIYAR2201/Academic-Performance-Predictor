# Database Schema — PostgreSQL

Normalized relational design (3NF). All tables use `BIGSERIAL` PKs, `TIMESTAMPTZ` timestamps,
and explicit FK constraints with `ON DELETE` policies chosen per relationship semantics.

```sql
-- ============================================================
-- ENUMS
-- ============================================================
CREATE TYPE user_role AS ENUM ('student', 'instructor', 'admin', 'super_admin');
CREATE TYPE enrollment_status AS ENUM ('active', 'completed', 'dropped', 'withdrawn');
CREATE TYPE assessment_type AS ENUM ('quiz', 'assignment', 'midterm', 'final', 'project', 'lab');
CREATE TYPE risk_level AS ENUM ('LOW', 'MEDIUM', 'HIGH');
CREATE TYPE prediction_type AS ENUM ('classification', 'gpa_regression');
CREATE TYPE preprocessing_status AS ENUM ('pending', 'validated', 'failed', 'processed');
CREATE TYPE direction_type AS ENUM ('positive', 'negative');

-- ============================================================
-- CORE IDENTITY
-- ============================================================
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(150) NOT NULL,
    email           CITEXT UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            user_role NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_role ON users(role);

CREATE TABLE departments (
    id      BIGSERIAL PRIMARY KEY,
    name    VARCHAR(150) NOT NULL UNIQUE,
    code    VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE students (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    student_id          VARCHAR(30) NOT NULL UNIQUE,      -- institutional ID
    department_id       BIGINT NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    enrollment_year     INT NOT NULL CHECK (enrollment_year BETWEEN 2000 AND 2100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_students_department ON students(department_id);

CREATE TABLE instructors (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    employee_id     VARCHAR(30) NOT NULL UNIQUE,
    department_id   BIGINT NOT NULL REFERENCES departments(id) ON DELETE RESTRICT
);
CREATE INDEX idx_instructors_department ON instructors(department_id);

-- ============================================================
-- ACADEMIC STRUCTURE
-- ============================================================
CREATE TABLE courses (
    id              BIGSERIAL PRIMARY KEY,
    course_code     VARCHAR(20) NOT NULL UNIQUE,
    course_name     VARCHAR(200) NOT NULL,
    credit          NUMERIC(3,1) NOT NULL CHECK (credit > 0),
    department_id   BIGINT NOT NULL REFERENCES departments(id) ON DELETE RESTRICT
);
CREATE INDEX idx_courses_department ON courses(department_id);

CREATE TABLE semesters (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,          -- e.g. "Spring"
    year        INT NOT NULL,
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    UNIQUE (name, year),
    CHECK (end_date > start_date)
);

-- course ↔ instructor assignment (drives RBAC scoping)
CREATE TABLE course_instructors (
    id              BIGSERIAL PRIMARY KEY,
    course_id       BIGINT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    instructor_id   BIGINT NOT NULL REFERENCES instructors(id) ON DELETE CASCADE,
    semester_id     BIGINT NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
    UNIQUE (course_id, instructor_id, semester_id)
);

CREATE TABLE enrollments (
    id                  BIGSERIAL PRIMARY KEY,
    student_id          BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id           BIGINT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    semester_id         BIGINT NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
    enrollment_status   enrollment_status NOT NULL DEFAULT 'active',
    UNIQUE (student_id, course_id, semester_id)
);
CREATE INDEX idx_enrollments_student ON enrollments(student_id);
CREATE INDEX idx_enrollments_course ON enrollments(course_id);

-- ============================================================
-- PERFORMANCE DATA
-- ============================================================
CREATE TABLE assessments (
    id                  BIGSERIAL PRIMARY KEY,
    enrollment_id       BIGINT NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    assessment_type     assessment_type NOT NULL,
    score               NUMERIC(6,2) NOT NULL CHECK (score >= 0),
    maximum_score       NUMERIC(6,2) NOT NULL CHECK (maximum_score > 0),
    assessment_date     DATE NOT NULL,
    CHECK (score <= maximum_score)
);
CREATE INDEX idx_assessments_enrollment ON assessments(enrollment_id);

CREATE TABLE attendance (
    id                      BIGSERIAL PRIMARY KEY,
    enrollment_id           BIGINT NOT NULL UNIQUE REFERENCES enrollments(id) ON DELETE CASCADE,
    total_classes           INT NOT NULL CHECK (total_classes >= 0),
    attended_classes        INT NOT NULL CHECK (attended_classes >= 0),
    attendance_percentage   NUMERIC(5,2) GENERATED ALWAYS AS (
        CASE WHEN total_classes = 0 THEN 0
        ELSE ROUND((attended_classes::NUMERIC / total_classes) * 100, 2) END
    ) STORED,
    CHECK (attended_classes <= total_classes)
);

CREATE TABLE academic_records (
    id              BIGSERIAL PRIMARY KEY,
    student_id      BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    semester_id     BIGINT NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
    course_id       BIGINT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    grade           VARCHAR(4) NOT NULL,           -- e.g. 'A', 'B+'
    grade_point     NUMERIC(3,2) NOT NULL CHECK (grade_point BETWEEN 0 AND 4.0),
    gpa             NUMERIC(3,2) CHECK (gpa BETWEEN 0 AND 4.0),  -- cumulative snapshot
    UNIQUE (student_id, semester_id, course_id)
);
CREATE INDEX idx_academic_records_student ON academic_records(student_id);

-- ============================================================
-- ML / DATASETS
-- ============================================================
CREATE TABLE datasets (
    id                      BIGSERIAL PRIMARY KEY,
    name                    VARCHAR(150) NOT NULL,
    version                 VARCHAR(30) NOT NULL,
    file_path               TEXT NOT NULL,
    row_count               INT NOT NULL CHECK (row_count >= 0),
    uploaded_by             BIGINT REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    preprocessing_status    preprocessing_status NOT NULL DEFAULT 'pending',
    UNIQUE (name, version)
);

CREATE TABLE ml_models (
    id                      BIGSERIAL PRIMARY KEY,
    name                    VARCHAR(150) NOT NULL,
    version                 VARCHAR(30) NOT NULL,
    algorithm               VARCHAR(100) NOT NULL,
    task_type               prediction_type NOT NULL,
    metrics                 JSONB NOT NULL,           -- {"accuracy":0.81,"f1":0.78,...}
    training_dataset_id     BIGINT NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    is_production           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);
-- only one production model per task_type
CREATE UNIQUE INDEX idx_one_production_per_task
    ON ml_models(task_type) WHERE is_production = TRUE;

CREATE TABLE predictions (
    id                  BIGSERIAL PRIMARY KEY,
    student_id          BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    model_version        VARCHAR(30) NOT NULL,
    prediction_type      prediction_type NOT NULL,
    predicted_value      NUMERIC(6,3) NOT NULL,        -- GPA value or encoded class score
    risk_level           risk_level,
    confidence           NUMERIC(4,3) CHECK (confidence BETWEEN 0 AND 1),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_predictions_student ON predictions(student_id, created_at DESC);

CREATE TABLE prediction_explanations (
    id              BIGSERIAL PRIMARY KEY,
    prediction_id   BIGINT NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    feature         VARCHAR(100) NOT NULL,
    contribution    NUMERIC(6,4) NOT NULL,     -- SHAP value
    direction       direction_type NOT NULL
);
CREATE INDEX idx_explanations_prediction ON prediction_explanations(prediction_id);

-- ============================================================
-- AUDIT
-- ============================================================
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(100) NOT NULL,
    entity_type     VARCHAR(100) NOT NULL,
    entity_id       BIGINT,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata        JSONB
);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
```

## Design notes

- `attendance_percentage` is a **generated column** — never write-conflicting with `attended/total`.
- `idx_one_production_per_task` is a **partial unique index** — enforces "exactly one production model per prediction task" at the DB level, not just app logic.
- `academic_records.gpa` stores a cumulative snapshot at time of record insert (for trend charts); current GPA is also derivable on the fly.
- All FK `ON DELETE` choices: `CASCADE` for strictly dependent child rows (e.g. a student's enrollments), `RESTRICT` for reference data that must not silently vanish (departments, datasets referenced by models), `SET NULL` for optional provenance (who uploaded/acted).
- `CITEXT` used for `email` for case-insensitive uniqueness (requires `CREATE EXTENSION citext`).
- Alembic will manage all migrations from this baseline; this file is the source-of-truth spec, not the literal migration script.
