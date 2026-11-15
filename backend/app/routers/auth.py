"""Authentication router."""
from fastapi import APIRouter, HTTPException, status, Response, Depends
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import bcrypt
from pymongo.errors import AutoReconnect, DuplicateKeyError, NetworkTimeout, PyMongoError, ServerSelectionTimeoutError
from ..models.user import UserCreate, UserResponse, LoginRequest
from ..database import ensure_database, get_database
from ..utils.jwt_handler import create_access_token, get_current_user
from ..utils.rate_limit import RateLimiter
from ..config import settings
from ..demo_user import DEMO_USER, is_demo_credentials, public_demo_user


router = APIRouter(prefix="/api/auth", tags=["auth"])

# Throttle credential endpoints to slow brute-force / spam attempts.
login_rate_limit = RateLimiter(times=10, seconds=60)
register_rate_limit = RateLimiter(times=5, seconds=60)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


@router.post("/register", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(register_rate_limit)])
async def register(user_data: UserCreate, response: Response):
    """Register new user."""
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    try:
        db = await ensure_database()
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        user_dict = {
            "email": user_data.email,
            "password_hash": hash_password(user_data.password),
            "full_name": user_data.full_name,
            "child_name": user_data.child_name,
            "child_age": user_data.child_age,
            "language": user_data.language,
            "role": "user",
            "created_at": datetime.utcnow(),
            "last_login": None,
            "total_sessions": 0,
            "total_stars": 0,
        }
        result = await db.users.insert_one(user_dict)

    except HTTPException:
        raise
    except DuplicateKeyError:
        # Handles two registration clicks racing for the same email.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    except (AutoReconnect, NetworkTimeout, ServerSelectionTimeoutError, PyMongoError) as error:
        print(f"[WARN] Registration database error: {type(error).__name__}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration is temporarily unavailable. Please try again in a moment.",
        )

    access_token = create_access_token(data={"sub": user_data.email, "role": "user"})
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    return {
        "message": "User registered successfully",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(result.inserted_id),
            "email": user_data.email,
            "full_name": user_data.full_name,
            "child_name": user_data.child_name,
            "child_age": user_data.child_age,
            "language": user_data.language,
            "role": "user",
            "total_sessions": 0,
            "total_stars": 0,
        },
    }


@router.post("/login", dependencies=[Depends(login_rate_limit)])
async def login(login_data: LoginRequest, response: Response):
    """Login user."""
    if is_demo_credentials(login_data.email, login_data.password):
        access_token = create_access_token(
            data={"sub": DEMO_USER["email"], "role": DEMO_USER["role"]}
        )
        response.set_cookie(
            key=settings.ACCESS_COOKIE_NAME,
            value=access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite=settings.COOKIE_SAMESITE,
            secure=settings.COOKIE_SECURE,
            path="/",
        )
        return {
            "message": "Demo login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user": public_demo_user(),
        }

    db = get_database()

    # Find user (admin accounts are seeded from env at startup; no hardcoded
    # credentials live in source. See seed_admin_user() in main.py.)
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Blocked accounts cannot log in (admin can block from the panel).
    if user.get("blocked"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked. Please contact support."
        )

    # Update last login and record a session row (feeds /auth/sessions).
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    await db.sessions.insert_one({
        "user_id": str(user["_id"]),
        "email": user["email"],
        "created_at": datetime.utcnow(),
        "platform": "web",
    })
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]}
    )
    
    # Set HTTP-only cookie
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    
    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "full_name": user["full_name"],
            "child_name": user["child_name"],
            "child_age": user.get("child_age", 0),
            "role": user["role"],
            "total_sessions": user.get("total_sessions", 0),
            "total_stars": user.get("total_stars", 0)
        }
    }


@router.post("/admin/login", dependencies=[Depends(login_rate_limit)])
async def admin_login(login_data: LoginRequest, response: Response):
    """Admin login."""
    db = get_database()
    
    # Find user
    user = await db.users.find_one({"email": login_data.email, "role": "admin"})
    if not user or not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": user["email"], "role": "admin"}
    )
    
    # Set HTTP-only cookie
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    
    return {
        "message": "Admin login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "full_name": user["full_name"],
            "role": "admin"
        }
    }


@router.post("/logout")
async def logout(response: Response):
    """Logout user."""
    response.delete_cookie(key=settings.ACCESS_COOKIE_NAME, path="/")
    return {"message": "Logout successful"}


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change the current user's password."""
    db = get_database()

    user = await db.users.find_one({"email": current_user["email"]})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password"
        )

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )

    return {"message": "Password changed successfully"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info."""
    return {
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "child_name": current_user.get("child_name"),
        "role": current_user["role"],
        "total_sessions": current_user.get("total_sessions", 0),
        "total_stars": current_user.get("total_stars", 0),
        "language": current_user.get("language", "Tamil")
    }
