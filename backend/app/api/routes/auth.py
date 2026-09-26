from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    user = auth_service.register_user(db, payload)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate(db, payload)
    return auth_service.issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return auth_service.refresh_access_token(db, payload.refresh_token)


@router.post("/logout", status_code=204)
def logout() -> None:
    # Stateless JWTs: logout is enforced client-side by discarding tokens.
    # A production deployment would blacklist the token's jti in Redis here
    # until it naturally expires; documented as a follow-up (see docs/security.md).
    return None


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
