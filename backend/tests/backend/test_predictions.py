from tests.conftest import register_and_login


def _setup_student_with_data(client):
    admin_token, _ = register_and_login(client, "Admin", "admin@test.edu", "password123", "admin")
    h = {"Authorization": f"Bearer {admin_token}"}

    dept = client.post("/api/departments", json={"name": "CS", "code": "CS1"}, headers=h).json()
    course = client.post(
        "/api/courses",
        json={"course_code": "C101", "course_name": "Intro", "credit": 3, "department_id": dept["id"]},
        headers=h,
    ).json()
    semester = client.post(
        "/api/semesters",
        json={"name": "Spring", "year": 2026, "start_date": "2026-01-01", "end_date": "2026-05-01"},
        headers=h,
    ).json()

    student_token, student_user_id = register_and_login(client, "Dana", "dana@test.edu", "password123", "student")
    student = client.post(
        "/api/students",
        json={"user_id": student_user_id, "student_id": "S-1", "department_id": dept["id"], "enrollment_year": 2024},
        headers=h,
    ).json()
    enrollment = client.post(
        "/api/enrollments",
        json={"student_id": student["id"], "course_id": course["id"], "semester_id": semester["id"]},
        headers=h,
    ).json()
    client.post(
        "/api/assessments",
        json={
            "enrollment_id": enrollment["id"],
            "assessment_type": "midterm",
            "score": 70,
            "maximum_score": 100,
            "assessment_date": "2026-03-01",
        },
        headers=h,
    )
    client.post(
        "/api/attendance",
        json={"enrollment_id": enrollment["id"], "total_classes": 30, "attended_classes": 25},
        headers=h,
    )
    return admin_token, student, student_token


def test_student_can_generate_own_prediction(client):
    _, student, student_token = _setup_student_with_data(client)
    resp = client.post(
        f"/api/predictions/students/{student['id']}", headers={"Authorization": f"Bearer {student_token}"}
    )
    assert resp.status_code == 201
    body = resp.json()

    assert body["classification"]["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert 0.0 <= body["classification"]["confidence"] <= 1.0
    assert 0.0 <= body["regression"]["predicted_gpa"] <= 4.0
    assert len(body["classification"]["explanation"]) > 0
    assert "estimate" in body["disclaimer"].lower()


def test_other_student_cannot_access_prediction(client):
    _, student, _ = _setup_student_with_data(client)
    other_token, _ = register_and_login(client, "Eve", "eve@test.edu", "password123", "student")

    resp = client.post(
        f"/api/predictions/students/{student['id']}", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert resp.status_code == 403


def test_admin_can_access_any_student_prediction(client):
    admin_token, student, _ = _setup_student_with_data(client)
    resp = client.post(
        f"/api/predictions/students/{student['id']}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
