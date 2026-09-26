from tests.conftest import register_and_login


def _bootstrap_course_structure(client):
    """Creates dept/course-A/course-B/semester as admin; returns ids + admin token."""
    admin_token, _ = register_and_login(client, "Admin", "admin@test.edu", "password123", "admin")
    h = {"Authorization": f"Bearer {admin_token}"}

    dept = client.post("/api/departments", json={"name": "CS", "code": "CS1"}, headers=h).json()
    course_a = client.post(
        "/api/courses",
        json={"course_code": "C101", "course_name": "Intro A", "credit": 3, "department_id": dept["id"]},
        headers=h,
    ).json()
    course_b = client.post(
        "/api/courses",
        json={"course_code": "C102", "course_name": "Intro B", "credit": 3, "department_id": dept["id"]},
        headers=h,
    ).json()
    semester = client.post(
        "/api/semesters",
        json={"name": "Spring", "year": 2026, "start_date": "2026-01-01", "end_date": "2026-05-01"},
        headers=h,
    ).json()
    return admin_token, dept, course_a, course_b, semester


def test_student_cannot_create_department(client):
    _, _ = register_and_login(client, "Student", "s@test.edu", "password123", "student")
    student_token, _ = register_and_login(client, "Student2", "s2@test.edu", "password123", "student")
    resp = client.post(
        "/api/departments",
        json={"name": "Physics", "code": "PHY"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


def test_instructor_can_only_grade_assigned_course(client):
    admin_token, dept, course_a, course_b, semester = _bootstrap_course_structure(client)
    h_admin = {"Authorization": f"Bearer {admin_token}"}

    instructor_token, instructor_user_id = register_and_login(
        client, "Bob", "bob@test.edu", "password123", "instructor"
    )
    student_token, student_user_id = register_and_login(client, "Carol", "carol@test.edu", "password123", "student")
    h_instructor = {"Authorization": f"Bearer {instructor_token}"}

    instructor = client.post(
        "/api/instructors",
        json={"user_id": instructor_user_id, "employee_id": "EMP-1", "department_id": dept["id"]},
        headers=h_admin,
    ).json()
    student = client.post(
        "/api/students",
        json={"user_id": student_user_id, "student_id": "S-1", "department_id": dept["id"], "enrollment_year": 2024},
        headers=h_admin,
    ).json()

    # Bob is assigned to teach ONLY course A
    client.post(
        f"/api/courses/{course_a['id']}/instructors",
        json={"instructor_id": instructor["id"], "semester_id": semester["id"]},
        headers=h_admin,
    )

    enroll_a = client.post(
        "/api/enrollments",
        json={"student_id": student["id"], "course_id": course_a["id"], "semester_id": semester["id"]},
        headers=h_admin,
    ).json()
    enroll_b = client.post(
        "/api/enrollments",
        json={"student_id": student["id"], "course_id": course_b["id"], "semester_id": semester["id"]},
        headers=h_admin,
    ).json()

    # Bob CAN grade enrollment A (his course)
    resp_a = client.post(
        "/api/assessments",
        json={
            "enrollment_id": enroll_a["id"],
            "assessment_type": "midterm",
            "score": 85,
            "maximum_score": 100,
            "assessment_date": "2026-03-01",
        },
        headers=h_instructor,
    )
    assert resp_a.status_code == 201

    # Bob CANNOT grade enrollment B (not his course)
    resp_b = client.post(
        "/api/assessments",
        json={
            "enrollment_id": enroll_b["id"],
            "assessment_type": "midterm",
            "score": 90,
            "maximum_score": 100,
            "assessment_date": "2026-03-01",
        },
        headers=h_instructor,
    )
    assert resp_b.status_code == 403
    assert resp_b.json()["code"] == "not_assigned_instructor"

    # Carol (the student) cannot grade her own enrollment
    resp_student = client.post(
        "/api/assessments",
        json={
            "enrollment_id": enroll_a["id"],
            "assessment_type": "quiz",
            "score": 10,
            "maximum_score": 10,
            "assessment_date": "2026-03-01",
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp_student.status_code == 403
