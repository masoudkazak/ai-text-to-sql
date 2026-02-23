"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import clear_auth_cookie, create_access_token, get_current_user, set_auth_cookie, verify_password
from models.user import User
from schemas.user import LoginRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    """Login and set JWT cookie."""

    result = await db.execute(select(User).where(User.email == payload.email, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id), user.role.value, user.allowed_tables)
    set_auth_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """Logout and clear JWT cookie."""

    clear_auth_cookie(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    """Return currently logged-in user."""

    return UserOut.model_validate(user)
