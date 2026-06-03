from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import get_db
from app.models.ladm import AppUser
from app.core.security import verify_password, hash_password, create_access_token
from app.schemas.ladm import TokenResponse, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse, summary="Obtain JWT access token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login with username + password. Returns JWT token. Roles: admin | planner | user"""
    result = await db.execute(select(AppUser).where(AppUser.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return TokenResponse(access_token=create_access_token(user.id, role=user.role))


@router.post("/register", response_model=UserOut, status_code=201,
             summary="Register a new user")
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(AppUser).where(AppUser.username == data.username))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")
    user = AppUser(
        username=data.username, email=data.email,
        hashed_password=hash_password(data.password), role=data.role
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
