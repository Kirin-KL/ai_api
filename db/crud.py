from datetime import datetime

from db.models import (
    Client, Phone, Address, MeterType, Meter,
    Zone, Reading, User, Role, Permission,
    RolePermission, UserRole, AuditLog
)

from sqlalchemy import select, asc, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, Optional, Type, Sequence
from sqlalchemy.inspection import inspect

from fastapi import HTTPException, status


# ===== Универсальный Query Builder =====

async def query_objects(
        db: AsyncSession,
        model: Type[Any],
        *,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False) -> Sequence[Any]:

    stmt = select(model)

    # --- Soft delete ---
    if not include_deleted and hasattr(model, "deleted_at"):
        stmt = stmt.where(model.deleted_at.is_(None))

    # --- Фильтры ---
    if filters:
        conditions = []
        mapper = inspect(model)

        for key, value in filters.items():
            if "__" in key:
                field, op = key.split("__", 1)
            else:
                field, op = key, "eq"

            if field not in mapper.columns:
                continue

            column = mapper.columns[field]

            # Операторы
            if op == "eq":
                conditions.append(column == value)
            elif op == "contains":
                conditions.append(column.ilike(f"%{value}%"))
            elif op == "gt":
                conditions.append(column > value)
            elif op == "lt":
                conditions.append(column < value)
            elif op == "gte":
                conditions.append(column >= value)
            elif op == "lte":
                conditions.append(column <= value)
            elif op == "in" and isinstance(value, list):
                conditions.append(column.in_(value))

        if conditions:
            stmt = stmt.where(and_(*conditions))

    # --- Сортировка ---
    if sort_by:
        mapper = inspect(model)
        direction = asc

        if sort_by.startswith("-"):
            direction = desc
            sort_by = sort_by[1:]

        if sort_by in mapper.columns:
            stmt = stmt.order_by(direction(mapper.columns[sort_by]))

    # --- Пагинация ---
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()

# Проверка разрешений у пользователя
async def check_permission(
    db: AsyncSession,
    role_id: int,
    resource: str,
    action: str,
):
    # Ищем нужное разрешение
    perm_stmt = select(Permission).where(
        Permission.resource == resource,
        Permission.action == action,
        Permission.deleted_at.is_(None),
    )
    perm_result = await db.execute(perm_stmt)
    permission = perm_result.scalar_one_or_none()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Разрешение {resource}:{action} не найдено",
        )

    # Проверяем связку role_permissions
    rp_stmt = select(RolePermission.id).where(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission.id,
        RolePermission.deleted_at.is_(None),
    )
    rp_result = await db.execute(rp_stmt)
    role_permission = rp_result.scalar_one_or_none()

    if not role_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    return True

# ===== Вспомогательная функция: сериализация модели в dict =====

# def model_to_dict(obj) -> Dict[str, Any]:
#     if obj is None:
#         return {}
#     mapper = inspect(obj.__class__)
#     data = {}
#     for column in mapper.columns:
#         name = column.key
#         data[name] = getattr(obj, name)
#         # Проверка на формат даты и перевод в строку, так как при записи в json дата не поддерживается
#         if isinstance(data[name], datetime):
#             data[name] = str(data[name])
#     return data

def model_to_dict(obj) -> Dict[str, Any]:
    if obj is None:
        return {}

    data = obj.__dict__.copy()
    data.pop("_sa_instance_state", None)

    for key, value in list(data.items()):
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, list):
            # если вдруг туда попали relationship-объекты, их лучше не тащить
            data[key] = [str(x) for x in value]

    return data


# ===== Аудит =====

async def log_audit(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: int,
    action: str,
    old_data: Optional[Dict[str, Any]],
    new_data: Optional[Dict[str, Any]],
    changed_by: Optional[int],
):
    log = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_data=old_data,
        new_data=new_data,
        changed_by=changed_by,
    )
    db.add(log)


# ===== Базовые CRUD-утилиты для любых моделей =====
#
async def get_by_id(db: AsyncSession, model: Type[Any],obj_id: int) -> Optional[Any]:
    return await db.get(model, obj_id)


async def get_all(db: AsyncSession, model: Type[Any], limit: int = 100, offset: int = 0) -> Sequence[Any]:
    stmt = select(model).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_object(db: AsyncSession, model: Type[Any], data: Dict[str, Any], *,
                        changed_by: Optional[int] = None,do_commit: bool = True) -> Any:
    obj = model(**data)
    db.add(obj)
    await db.flush()  # чтобы получить id

    await log_audit(
        db,
        table_name=model.__tablename__,
        record_id=obj.id,
        action="create",
        old_data=None,
        new_data=model_to_dict(obj),
        changed_by=changed_by,
    )

    if do_commit:
        await db.commit()
        await db.refresh(obj)

    return obj


async def update_object(db: AsyncSession, obj: Any, data: Dict[str, Any], *, changed_by: Optional[int] = None,
                        do_commit: bool = True) -> Any:
    old = model_to_dict(obj)

    for key, value in data.items():
        setattr(obj, key, value)

    await db.flush()

    new = model_to_dict(obj)

    await log_audit(
        db,
        table_name=obj.__tablename__,
        record_id=obj.id,
        action="update",
        old_data=old,
        new_data=new,
        changed_by=changed_by,
    )

    if do_commit:
        await db.commit()
        await db.refresh(obj)

    return obj


async def soft_delete_object(db: AsyncSession, obj: Any, *, changed_by: Optional[int] = None,
                             do_commit: bool = True) -> Any:
    old = model_to_dict(obj)

    # предполагаем, что везде есть deleted_at
    from sqlalchemy.sql import func
    obj.deleted_at = func.now()

    await db.flush()

    new = model_to_dict(obj)

    await log_audit(
        db,
        table_name=obj.__tablename__,
        record_id=obj.id,
        action="delete",
        old_data=old,
        new_data=new,
        changed_by=changed_by,
    )

    if do_commit:
        await db.commit()
        await db.refresh(obj)

    return obj

# Операции для объектов сущностей

# ===== Клиенты =====

async def create_client(
        db: AsyncSession,
        *,
        last_name: str,
        first_name: str,
        middle_name: Optional[str],
        account_number: str,
        changed_by: Optional[int] = None) -> Client:

    data = {
        "last_name": last_name,
        "first_name": first_name,
        "middle_name": middle_name,
        "account_number": account_number,
    }
    return await create_object(db, Client, data, changed_by=changed_by)


async def update_client(
        db: AsyncSession,
        client_id: int,
        data: Dict[str, Any],
        *,
        changed_by: Optional[int] = None) -> Optional[Client]:

    client = await get_by_id(db, Client, client_id)
    if not client:
        return None
    return await update_object(db, client, data, changed_by=changed_by)


async def soft_delete_client(
        db: AsyncSession,
        client_id: int,
        *,
        changed_by: Optional[int] = None
) -> Optional[Client]:

    client = await get_by_id(db, Client, client_id)
    if not client:
        return None
    return await soft_delete_object(db, client, changed_by=changed_by)


# ===== Показания =====

async def create_reading(
        db: AsyncSession,
        *,
        meter_id: int,
        zone_id: int,
        value: int,
        date,
        submitted_by: Optional[int],
        changed_by: Optional[int] = None) -> Reading:

    data = {
        "meter_id": meter_id,
        "zone_id": zone_id,
        "value": value,
        "date": date,
        "submitted_by": submitted_by,
    }
    return await create_object(db, Reading, data, changed_by=changed_by)


async def update_reading(
        db: AsyncSession,
        reading_id: int,
        data: Dict[str, Any],
        *,
        changed_by: Optional[int] = None) -> Optional[Reading]:

    reading = await get_by_id(db, Reading, reading_id)
    if not reading:
        return None
    return await update_object(db, reading, data, changed_by=changed_by)


async def soft_delete_reading(
        db: AsyncSession,
        reading_id: int,
        *,
        changed_by: Optional[int] = None) -> Optional[Reading]:

    reading = await get_by_id(db, Reading, reading_id)
    if not reading:
        return None
    return await soft_delete_object(db, reading, changed_by=changed_by)


# ===== Телефоны =====

async def create_phone(
    db: AsyncSession,
    *,
    client_id: int,
    phone_number: str,
    is_primary: bool = False,
    changed_by: Optional[int] = None
) -> Phone:
    data = {
        "client_id": client_id,
        "phone_number": phone_number,
        "is_primary": is_primary,
    }
    return await create_object(db, Phone, data, changed_by=changed_by)


async def update_phone(
    db: AsyncSession,
    phone_id: int,
    data: Dict[str, Any],
    *,
    changed_by: Optional[int] = None
) -> Optional[Phone]:
    phone = await get_by_id(db, Phone, phone_id)
    if not phone:
        return None
    return await update_object(db, phone, data, changed_by=changed_by)


async def soft_delete_phone(
    db: AsyncSession,
    phone_id: int,
    *,
    changed_by: Optional[int] = None
) -> Optional[Phone]:
    phone = await get_by_id(db, Phone, phone_id)
    if not phone:
        return None
    return await soft_delete_object(db, phone, changed_by=changed_by)


# ===== Адреса =====

async def create_address(
    db: AsyncSession,
    *,
    client_id: int,
    city: str,
    street: str,
    house: str,
    flat: str,
    changed_by: Optional[int] = None
) -> Address:
    data = {
        "client_id": client_id,
        "city": city,
        "street": street,
        "house": house,
        "flat": flat,
    }
    return await create_object(db, Address, data, changed_by=changed_by)


async def update_address(
    db: AsyncSession,
    address_id: int,
    data: Dict[str, Any],
    *,
    changed_by: Optional[int] = None
) -> Optional[Address]:
    address = await get_by_id(db, Address, address_id)
    if not address:
        return None
    return await update_object(db, address, data, changed_by=changed_by)


async def soft_delete_address(
    db: AsyncSession,
    address_id: int,
    *,
    changed_by: Optional[int] = None
) -> Optional[Address]:
    address = await get_by_id(db, Address, address_id)
    if not address:
        return None
    return await soft_delete_object(db, address, changed_by=changed_by)


# ===== Типы ПУ =====

async def create_meter_type(
    db: AsyncSession,
    *,
    name: str,
    changed_by: Optional[int] = None
) -> MeterType:
    data = {"name": name}
    return await create_object(db, MeterType, data, changed_by=changed_by)


async def update_meter_type(
    db: AsyncSession,
    type_id: int,
    data: Dict[str, Any],
    *,
    changed_by: Optional[int] = None
) -> Optional[MeterType]:
    mt = await get_by_id(db, MeterType, type_id)
    if not mt:
        return None
    return await update_object(db, mt, data, changed_by=changed_by)


async def soft_delete_meter_type(
    db: AsyncSession,
    type_id: int,
    *,
    changed_by: Optional[int] = None
) -> Optional[MeterType]:
    mt = await get_by_id(db, MeterType, type_id)
    if not mt:
        return None
    return await soft_delete_object(db, mt, changed_by=changed_by)


# ===== ПУ =====

async def create_meter(
    db: AsyncSession,
    *,
    serial_number: str,
    name: str,
    client_id: int,
    type_id: int,
    changed_by: Optional[int] = None
) -> Meter:
    data = {
        "serial_number": serial_number,
        "name": name,
        "client_id": client_id,
        "type_id": type_id,
    }
    return await create_object(db, Meter, data, changed_by=changed_by)


async def update_meter(
    db: AsyncSession,
    meter_id: int,
    data: Dict[str, Any],
    *,
    changed_by: Optional[int] = None
) -> Optional[Meter]:
    meter = await get_by_id(db, Meter, meter_id)
    if not meter:
        return None
    return await update_object(db, meter, data, changed_by=changed_by)


async def soft_delete_meter(
    db: AsyncSession,
    meter_id: int,
    *,
    changed_by: Optional[int] = None
) -> Optional[Meter]:
    meter = await get_by_id(db, Meter, meter_id)
    if not meter:
        return None
    return await soft_delete_object(db, meter, changed_by=changed_by)


# ===== Зоны =====

async def create_zone(
    db: AsyncSession,
    *,
    name: str,
    description: Optional[str],
    changed_by: Optional[int] = None
) -> Zone:
    data = {"name": name, "description": description}
    return await create_object(db, Zone, data, changed_by=changed_by)


async def update_zone(
    db: AsyncSession,
    zone_id: int,
    data: Dict[str, Any],
    *,
    changed_by: Optional[int] = None
) -> Optional[Zone]:
    zone = await get_by_id(db, Zone, zone_id)
    if not zone:
        return None
    return await update_object(db, zone, data, changed_by=changed_by)


async def soft_delete_zone(
    db: AsyncSession,
    zone_id: int,
    *,
    changed_by: Optional[int] = None
) -> Optional[Zone]:
    zone = await get_by_id(db, Zone, zone_id)
    if not zone:
        return None
    return await soft_delete_object(db, zone, changed_by=changed_by)


# ===== Пользователи =====

async def create_user(
        db: AsyncSession,
        *,
        full_name: str,
        nickname: str,
        email: str,
        password_hash: str,
        last_login_at: datetime,
        changed_by: Optional[int] = None

) -> User:
    data = {
        "full_name": full_name,
        "nickname": nickname,
        "email": email,
        "password_hash": password_hash,
        "last_login_at": last_login_at
    }
    return await create_object(db, User, data, changed_by=changed_by)


async def update_user(
    db: AsyncSession,
    user_id: int,
    data: Dict[str, Any],
    *,
    changed_by: Optional[int] = None
) -> Optional[User]:
    user = await get_by_id(db, User, user_id)
    if not user:
        return None
    return await update_object(db, user, data, changed_by=changed_by)


async def soft_delete_user(
    db: AsyncSession,
    user_id: int,
    *,
    changed_by: Optional[int] = None
) -> Optional[User]:
    user = await get_by_id(db, User, user_id)
    if not user:
        return None
    return await soft_delete_object(db, user, changed_by=changed_by)


# ===== Роли =====

async def create_role(
    db: AsyncSession,
    *,
    name: str,
    description: Optional[str],
    changed_by: Optional[int] = None
) -> Role:
    data = {"name": name, "description": description}
    return await create_object(db, Role, data, changed_by=changed_by)


async def update_role(
    db: AsyncSession,
    role_id: int,
    data: Dict[str, Any],
    *,
    changed_by: Optional[int] = None
) -> Optional[Role]:
    role = await get_by_id(db, Role, role_id)
    if not role:
        return None
    return await update_object(db, role, data, changed_by=changed_by)


async def soft_delete_role(
    db: AsyncSession,
    role_id: int,
    *,
    changed_by: Optional[int] = None
) -> Optional[Role]:
    role = await get_by_id(db, Role, role_id)
    if not role:
        return None
    return await soft_delete_object(db, role, changed_by=changed_by)


# ===== Разрешения =====

async def create_permission(
    db: AsyncSession,
    *,
    resource: str,
    action: str,
    name: str,
    changed_by: Optional[int] = None
) -> Permission:
    data = {"resource": resource, "action": action, "name": name}
    return await create_object(db, Permission, data, changed_by=changed_by)


async def update_permission(
    db: AsyncSession,
    permission_id: int,
    data: Dict[str, Any],
    *,
    changed_by: Optional[int] = None
) -> Optional[Permission]:
    perm = await get_by_id(db, Permission, permission_id)
    if not perm:
        return None
    return await update_object(db, perm, data, changed_by=changed_by)


async def soft_delete_permission(
    db: AsyncSession,
    permission_id: int,
    *,
    changed_by: Optional[int] = None
) -> Optional[Permission]:
    perm = await get_by_id(db, Permission, permission_id)
    if not perm:
        return None
    return await soft_delete_object(db, perm, changed_by=changed_by)


# ===== RolePermission =====

async def create_permission_to_role(
    db: AsyncSession,
    *,
    role_id: int,
    permission_id: int,
    changed_by: Optional[int] = None
) -> RolePermission:
    data = {"role_id": role_id, "permission_id": permission_id}
    return await create_object(db, RolePermission, data, changed_by=changed_by)


async def soft_remove_permission_from_role(
    db: AsyncSession,
    role_permission_id:int,
    *,
    changed_by: Optional[int] = None
) -> Optional[RolePermission]:
    rp = await get_by_id(db, RolePermission, role_permission_id)
    if not rp:
        return None
    return await soft_delete_object(db, rp, changed_by=changed_by)


# ===== UserRole =====

async def create_role_to_user(
    db: AsyncSession,
    *,
    user_id: int,
    role_id: int,
    changed_by: Optional[int] = None
) -> UserRole:
    data = {
        "user_id": user_id,
        "role_id": role_id,
    }
    return await create_object(db, UserRole, data, changed_by=changed_by)


async def soft_remove_role_from_user(
    db: AsyncSession,
        user_roles_id:int,
    *,
    changed_by: Optional[int] = None
) -> Optional[UserRole]:
    ur = await get_by_id(db, UserRole, user_roles_id)
    if not ur:
        return None
    return await soft_delete_object(db, ur, changed_by=changed_by)



