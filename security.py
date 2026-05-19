from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

from fastapi import Header, HTTPException


# =========================
# Password hashing
# =========================
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def process_password(password: str, hashed_password: str = None) -> str or bool:
    """
    Универсальная функция для работы с паролями:
    - Если передан только password -> возвращает хэш
    - Если переданы password и hashed_password -> проверяет соответствие (для логина)
    """
    if hashed_password is None:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Пароль слишком длинный")
        return pwd_context.hash(password)
    else:
        return pwd_context.verify(password, hashed_password)


# =========================
# JWT settings
# =========================
SECRET_KEY = "your-secret-key-change-me10"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120


# =========================
# JWT create / decode
# =========================
def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except PyJWTError:
        return None



# def get_current_user(authorization: str = Header(None)):
#     if not authorization:
#         raise HTTPException(status_code=401, detail="Не авторизован")
#
#     if not authorization.startswith("Bearer "):
#         raise HTTPException(status_code=401, detail="Неверный формат токена (не Bearer)")
#
#     token = authorization.split(" ", 1)[1]
#     payload = decode_access_token(token)
#
#     if payload is None:
#         raise HTTPException(status_code=401, detail="Неверный или просроченный токен")
#
#     return payload


def get_current_user(authorization: str):

    token = authorization
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Неверный или просроченный токен")

    return payload