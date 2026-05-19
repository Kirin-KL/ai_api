
from fastapi import APIRouter, HTTPException
from shemas import Auth
import db.crud as db_crud
from db.database import get_async_db
from fastapi import Depends
from db.models import User, UserRole, Role
from security import process_password, create_access_token

router = APIRouter(prefix="/authorization", tags=["authorization"])


@router.post("/auth")
async def auth_user(
        payload: Auth,
        db = Depends(get_async_db)):

    filter_user = {"email":payload.user_login.strip()}

    user = await db_crud.query_objects(
        db = db,
        model=User,
        filters=filter_user,
        limit=1
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Пользователь не найден")

    user = user[0]

    password = payload.user_pass.strip()
    user_hash = user.password_hash

    password_check = process_password(
        password=password,
        hashed_password=user_hash
    )

    filter_role = {"user_id":user.id}

    role_user = await db_crud.query_objects(
        db = db,
        model=UserRole,
        filters=filter_role,
        limit=1
    )

    if not role_user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь без роли")

    role_user = role_user[0]

    role = await db_crud.get_by_id(
        db=db,
        model=Role,
        obj_id=role_user.role_id
    )

    if password_check:
        data = {
            "sub": str(user.id),
            "role": role.name,
            "role_id":role.id,
            "email": user.email,
        }

        jwt_token = create_access_token(data)

        return {"access_token": jwt_token, "token_type": "bearer"}

    else:
        raise HTTPException(
            status_code=401,
            detail="Неверный пароль"
        )
