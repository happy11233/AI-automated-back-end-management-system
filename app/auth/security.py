from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from app.config import settings
from app.db import fetch_one

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(data: dict[str, Any]) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = data.copy()
    payload.update({
        "exp": expires_at,
    })

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的 token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_user_by_username(username: str) -> dict | None:
    row = fetch_one(
        """
        SELECT id, username, role, department, password_hash
        FROM users
        WHERE username = %s;
        """,
        (username,),
    )

    if row is None:
        return None

    return {
        "id": str(row[0]),
        "username": row[1],
        "role": row[2],
        "department": row[3],
        "password_hash": row[4],
    }


def get_user_by_id(user_id: str) -> dict | None:
    row = fetch_one(
        """
        SELECT id, username, role, department
        FROM users
        WHERE id = %s;
        """,
        (user_id,),
    )

    if row is None:
        return None

    return {
        "id": str(row[0]),
        "username": row[1],
        "role": row[2],
        "department": row[3],
    }


def authenticate_user(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)

    if user is None:
        return None

    if not user["password_hash"]:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return user


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 缺少用户标识",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )

    return current_user