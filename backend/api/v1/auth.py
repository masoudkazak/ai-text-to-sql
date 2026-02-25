import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import clear_auth_cookie, create_access_token, get_current_user, hash_password, set_auth_cookie, verify_password
from middleware.rate_limiter import get_global_daily_usage, get_user_daily_usage
from models.enums import UserRole
from models.user import User
from schemas.user import LoginRequest, UsageSummaryOut, UserOut, UserRegister
from services.table_service import list_non_blacklisted_tables


DEFAULT_LIMITS = {
    UserRole.ADMIN: 20,
    UserRole.DEVELOPER: 12,
    UserRole.ANALYST: 8,
    UserRole.VIEWER: 6,
    UserRole.RESTRICTED: 4,
}

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    result = await db.execute(select(User).where(User.email == payload.email, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id), user.role.value, user.allowed_tables)
    set_auth_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    if not payload.name.strip() or not payload.password.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name and password are required")

    exists = await db.execute(select(User).where(User.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(
        name=payload.name,
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        role=UserRole.VIEWER,
        allowed_tables=[],
        daily_query_limit=DEFAULT_LIMITS[UserRole.VIEWER],
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.role.value, user.allowed_tables)
    set_auth_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/demo", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def demo_login(response: Response, db: AsyncSession = Depends(get_db)) -> UserOut:
    demo_name = f"Demo User {secrets.token_hex(4).upper()}"
    demo_email = f"demo_{secrets.token_hex(6)}@example.com"
    demo_password = secrets.token_urlsafe(12)

    user = User(
        name=demo_name,
        email=demo_email,
        hashed_password=hash_password(demo_password),
        role=UserRole.VIEWER,
        allowed_tables=[],
        daily_query_limit=DEFAULT_LIMITS[UserRole.VIEWER],
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.role.value, user.allowed_tables)
    set_auth_cookie(response, token)
    return UserOut.model_validate(user)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    clear_auth_cookie(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/usage-summary", response_model=UsageSummaryOut)
async def usage_summary(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> UsageSummaryOut:
    global_limit, global_used, global_remaining = await get_global_daily_usage()
    user_limit, user_used, user_remaining = await get_user_daily_usage(user)
    available_tables = await list_non_blacklisted_tables(db)
    return UsageSummaryOut(
        global_daily_limit=global_limit,
        global_used=global_used,
        global_remaining=global_remaining,
        user_daily_limit=user_limit,
        user_used=user_used,
        user_remaining=user_remaining,
        available_tables=available_tables,
    )
