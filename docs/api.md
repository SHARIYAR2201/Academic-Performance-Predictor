# API Documentation

Full interactive reference (auto-generated from the Pydantic schemas):
`http://localhost:8000/docs` (Swagger UI) or `/redoc`.

This document covers the parts that aren't obvious from the schema alone:
auth flow and RBAC rules.

## Authentication

```
POST /api/auth/register   {name, email, password, role}  -> 201 UserOut
POST /api/auth/login      {email, password}               -> 200 TokenResponse
POST /api/auth/refresh    {refresh_token}                  -> 200 TokenResponse
POST /api/auth/logout                                       -> 204
GET  /api/auth/me          (Bearer token)                  -> 200 UserOut
```

Access tokens expire after 30 minutes by default
(`ACCESS_TOKEN_EXPIRE_MINUTES`); refresh tokens after 7 days. Both are
plain JWTs (HS256) carrying `sub` (user id), `role`, and `type`
(`access`/`refresh`) claims — see `app/core/security.py`.

**Logout is stateless**: it doesn't blacklist the token server-side (see
README limitations). The client is expected to discard both tokens.

## Role-based access control

Every protected endpoint uses one of two dependency patterns
(`app/api/deps.py`):

- `get_current_user` — any authenticated user.
- `require_roles(*roles)` — restricts to specific roles at the route level
  (e.g. `require_roles(UserRole.admin, UserRole.super_admin)`).

Route-level role checks are necessary but not sufficient — the actual data
scoping (an instructor can only touch *their own* courses; a student can
only see *their own* data) is enforced in the service layer
(`app/services/academic_service.py`), not the route. This matters: two
different instructors both pass the `require_roles(instructor)` check, but
only one of them is authorized to write assessment data for a given
enrollment. See `assert_user_can_access_student` and
`_get_enrollment_scoped_for_write` for the actual logic, and
`tests/backend/test_rbac.py` for the automated proof.

## Prediction endpoint

```
POST /api/predictions/students/{student_id}   (Bearer token) -> 201 PredictionResponse
```

Authorization (`assert_user_can_access_student`):
- **student** — only if `student_id` resolves to their own profile.
- **instructor** — only if the student is currently enrolled in a course
  the instructor teaches (checked via the `course_instructors` join table).
- **admin / super_admin** — any student.

The response includes both the classification and regression predictions,
each with its SHAP-based feature explanation and a fixed disclaimer string
(`PredictionResponse.disclaimer`) reiterating that this is a model-generated
estimate. See [docs/machine-learning.md](machine-learning.md) for what goes
into the feature vector and how the explanation is computed.

Every call **persists** a new `predictions` row (one for classification, one
for regression) plus its `prediction_explanations` rows — predictions are
not just computed and returned, they become part of the historical record
(useful for the audit trail and for tracking a student's risk trend over
time, though a "risk history over time" chart is not yet built into the
frontend — future work).

## Error shape

Every error response (see `app/core/errors.py`) has the same shape:

```json
{"code": "not_assigned_instructor", "message": "You are not the assigned instructor for this course/semester."}
```

`code` is meant for the frontend to branch on; `message` is safe to show
directly to the user. Unhandled exceptions are caught and logged
server-side, and return a generic `internal_error` — no stack traces or
internals ever reach the client.
