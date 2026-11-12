from datetime import timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..auth.auth import authenticate_user, create_access_token, get_current_user, get_current_admin_user
from ..config import settings
from ..database import get_db
from ..models.user import User
from ..schemas.user import Token, User as UserSchema, UserCreate
from ..services.exceptions import UserAlreadyExistsError
from ..services.user_service import UserService
from ..dependencies import get_login_limiter, get_user_service
from ..services.login_limiter import LoginLimiter, LoginLimitExceeded, LoginLimiterUnavailable

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserSchema)
def register(user: UserCreate, current_admin: User = Depends(get_current_admin_user), user_service: UserService = Depends(get_user_service)):
    try:
        return user_service.register_user(user)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        ) from exc


@router.post("/login", response_model=Token, responses={
    401: {"description": "Incorrect username or password"},
    429: {
        "description": "Login attempt limit exceeded",
        "headers": {"Retry-After": {"schema": {"type": "integer", "minimum": 1}}},
    },
    503: {
        "description": "Authentication storage temporarily unavailable",
        "headers": {"Retry-After": {"schema": {"type": "integer", "minimum": 1}}},
    },
})
def login(
    request: Request, form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db), limiter: LoginLimiter = Depends(get_login_limiter),
):
    try:
        # Only the ASGI connection peer; never read client-supplied IP headers.
        source = request.client.host if request.client else "unknown"
        reservation = limiter.reserve(form_data.username, source)
        user = authenticate_user(db, form_data.username, form_data.password)
        if user:
            limiter.refund(reservation)
    except LoginLimitExceeded as exc:
        logger.warning("Login throttled")
        raise HTTPException(
            status_code=429, detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except (LoginLimiterUnavailable, SQLAlchemyError) as exc:
        logger.error("Login temporarily unavailable")
        raise HTTPException(
            status_code=503, detail="Authentication temporarily unavailable",
            headers={"Retry-After": "60"},
        ) from exc
    if not user:
        logger.info("Login failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
