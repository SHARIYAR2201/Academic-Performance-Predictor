$ErrorActionPreference = "Stop"
$Base = "http://127.0.0.1:8000/api"

function Invoke-Api {
    param($Method, $Path, $Body = $null, $Token = $null)
    $headers = @{}
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }
    $params = @{
        Method  = $Method
        Uri     = "$Base$Path"
        Headers = $headers
        ContentType = "application/json"
    }
    if ($Body) { $params["Body"] = ($Body | ConvertTo-Json) }
    return Invoke-RestMethod @params
}

Write-Host "=== 1. Registering admin ===" -ForegroundColor Cyan
try {
    Invoke-Api POST "/auth/register" @{name="Demo Admin"; email="admin@demo.edu"; password="password123"; role="admin"} | Out-Null
} catch { Write-Host "  (admin may already exist, continuing)" -ForegroundColor Yellow }
$adminLogin = Invoke-Api POST "/auth/login" @{email="admin@demo.edu"; password="password123"}
$adminToken = $adminLogin.access_token
Write-Host "  Admin token acquired." -ForegroundColor Green

Write-Host "=== 2. Creating department, course, semester ===" -ForegroundColor Cyan
$dept   = Invoke-Api POST "/departments" @{name="Computer Science"; code="CSDEMO"} $adminToken
$course = Invoke-Api POST "/courses" @{course_code="CS101DEMO"; course_name="Intro to Programming"; credit=3; department_id=$dept.id} $adminToken
$sem1   = Invoke-Api POST "/semesters" @{name="Fall"; year=2025; start_date="2025-09-01"; end_date="2025-12-15"} $adminToken
$sem2   = Invoke-Api POST "/semesters" @{name="Spring"; year=2026; start_date="2026-01-01"; end_date="2026-05-01"} $adminToken
Write-Host "  dept=$($dept.id) course=$($course.id) sem1=$($sem1.id) sem2=$($sem2.id)" -ForegroundColor Green

Write-Host "=== 3. Registering instructor + student users ===" -ForegroundColor Cyan
try { Invoke-Api POST "/auth/register" @{name="Demo Instructor"; email="instructor@demo.edu"; password="password123"; role="instructor"} | Out-Null } catch {}
try { Invoke-Api POST "/auth/register" @{name="Demo Student"; email="student@demo.edu"; password="password123"; role="student"} | Out-Null } catch {}
$instructorLogin = Invoke-Api POST "/auth/login" @{email="instructor@demo.edu"; password="password123"}
$studentLogin    = Invoke-Api POST "/auth/login" @{email="student@demo.edu"; password="password123"}
$instructorToken = $instructorLogin.access_token
$studentToken    = $studentLogin.access_token
$instructorUser  = Invoke-Api GET "/auth/me" -Token $instructorToken
$studentUser     = Invoke-Api GET "/auth/me" -Token $studentToken
Write-Host "  instructor_user_id=$($instructorUser.id) student_user_id=$($studentUser.id)" -ForegroundColor Green

Write-Host "=== 4. Creating instructor + student profiles ===" -ForegroundColor Cyan
$instructor = Invoke-Api POST "/instructors" @{user_id=$instructorUser.id; employee_id="EMP-DEMO-1"; department_id=$dept.id} $adminToken
$student    = Invoke-Api POST "/students" @{user_id=$studentUser.id; student_id="STU-DEMO-1"; department_id=$dept.id; enrollment_year=2024} $adminToken
Write-Host "  instructor_profile_id=$($instructor.id) student_profile_id=$($student.id)" -ForegroundColor Green

Write-Host "=== 5. Assigning instructor to course, enrolling student (past + current semester) ===" -ForegroundColor Cyan
Invoke-Api POST "/courses/$($course.id)/instructors" @{instructor_id=$instructor.id; semester_id=$sem2.id} $adminToken | Out-Null
$enrollPast    = Invoke-Api POST "/enrollments" @{student_id=$student.id; course_id=$course.id; semester_id=$sem1.id} $adminToken
$enrollCurrent = Invoke-Api POST "/enrollments" @{student_id=$student.id; course_id=$course.id; semester_id=$sem2.id} $adminToken
Write-Host "  enrollment_past=$($enrollPast.id) enrollment_current=$($enrollCurrent.id)" -ForegroundColor Green

Write-Host "=== 6. Recording current-semester grades + attendance (as the assigned instructor) ===" -ForegroundColor Cyan
Invoke-Api POST "/assessments" @{enrollment_id=$enrollCurrent.id; assessment_type="midterm"; score=72; maximum_score=100; assessment_date="2026-03-01"} $instructorToken | Out-Null
Invoke-Api POST "/assessments" @{enrollment_id=$enrollCurrent.id; assessment_type="quiz"; score=65; maximum_score=100; assessment_date="2026-03-05"} $instructorToken | Out-Null
Invoke-Api POST "/assessments" @{enrollment_id=$enrollCurrent.id; assessment_type="assignment"; score=80; maximum_score=100; assessment_date="2026-03-10"} $instructorToken | Out-Null
Invoke-Api POST "/attendance" @{enrollment_id=$enrollCurrent.id; total_classes=30; attended_classes=22} $instructorToken | Out-Null
Write-Host "  Grades + attendance recorded." -ForegroundColor Green

Write-Host "=== 7. Generating the real prediction (as the student) ===" -ForegroundColor Cyan
$prediction = Invoke-Api POST "/predictions/students/$($student.id)" -Token $studentToken
$prediction | ConvertTo-Json -Depth 6

Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Cyan
Write-Host "Student profile ID to use in the frontend: $($student.id)" -ForegroundColor Yellow
Write-Host "Log in at http://localhost:3000/login as:"
Write-Host "  Student:    student@demo.edu / password123"
Write-Host "  Instructor: instructor@demo.edu / password123  (course ID for roster: $($course.id))"