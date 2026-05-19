import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import AsyncSessionLocal
from db.models import Permission, Role, RolePermission, UserRole
from sqlalchemy.exc import IntegrityError


PERMISSIONS_DATA = [
    # Управление пользователями
    {"resource": "users", "action": "create", "name": "Создание пользователей"},
    {"resource": "users", "action": "read", "name": "Чтение пользователей"},
    {"resource": "users", "action": "update", "name": "Обновление пользователей"},
    {"resource": "users", "action": "delete", "name": "Удаление пользователей"},

    {"resource": "clients", "action": "create", "name": "Создание клиентов"},
    {"resource": "clients", "action": "read", "name": "Чтение клиентов"},
    {"resource": "clients", "action": "update", "name": "Обновление клиентов"},
    {"resource": "clients", "action": "delete", "name": "Удаление клиентов"},

    {"resource": "phones", "action": "create", "name": "Создание телефонов"},
    {"resource": "phones", "action": "read", "name": "Чтение телефонов"},
    {"resource": "phones", "action": "update", "name": "Обновление телефонов"},
    {"resource": "phones", "action": "delete", "name": "Удаление телефонов"},

    {"resource": "address", "action": "create", "name": "Создание адресов"},
    {"resource": "address", "action": "read", "name": "Чтение адресов"},
    {"resource": "address", "action": "update", "name": "Обновление адресов"},
    {"resource": "address", "action": "delete", "name": "Удаление адресов"},

    {"resource": "readings", "action": "create", "name": "Создание показаний"},
    {"resource": "readings", "action": "read", "name": "Чтение показаний"},
    {"resource": "readings", "action": "update", "name": "Обновление показаний"},
    {"resource": "readings", "action": "delete", "name": "Удаление показаний"},

    {"resource": "roles", "action": "create", "name": "Создание ролей"},
    {"resource": "roles", "action": "read", "name": "Чтение ролей"},
    {"resource": "roles", "action": "update", "name": "Обновление ролей"},
    {"resource": "roles", "action": "delete", "name": "Удаление ролей"},

    {"resource": "permissions", "action": "create", "name": "Создание разрешений"},
    {"resource": "permissions", "action": "read", "name": "Чтение разрешений"},
    {"resource": "permissions", "action": "update", "name": "Обновление разрешений"},
    {"resource": "permissions", "action": "delete", "name": "Удаление разрешений"},

    {"resource": "meter_types", "action": "create", "name": "Создание типов счетчиков"},
    {"resource": "meter_types", "action": "read", "name": "Чтение типов счетчиков"},
    {"resource": "meter_types", "action": "update", "name": "Обновление типов счетчиков"},
    {"resource": "meter_types", "action": "delete", "name": "Удаление типов счетчиков"},

    {"resource": "role_permissions", "action": "create", "name": "Создание разрешений ролей"},
    {"resource": "role_permissions", "action": "read", "name": "Чтение разрешений ролей"},
    {"resource": "role_permissions", "action": "update", "name": "Обновление разрешений ролей"},
    {"resource": "role_permissions", "action": "delete", "name": "Удаление разрешений ролей"},

    {"resource": "user_roles", "action": "create", "name": "Создание ролей пользователей"},
    {"resource": "user_roles", "action": "read", "name": "Чтение ролей пользователей"},
    {"resource": "user_roles", "action": "update", "name": "Обновление ролей пользователей"},
    {"resource": "user_roles", "action": "delete", "name": "Удаление ролей пользователей"},
]

ROLES_DATA = [
    {"name": "admin", "description": "Администратор (полный доступ)"},
    {"name": "system_manager", "description": "Управление системой (справочники, без клиентов)"},
    {"name": "viewer", "description": "Только просмотр показаний"},
]

ROLE_PERMISSIONS_DATA = {
    "admin": [
        {"resource": "users", "action": "create"},
        {"resource": "users", "action": "read"},
        {"resource": "users", "action": "update"},
        {"resource": "users", "action": "delete"},

        {"resource": "clients", "action": "create"},
        {"resource": "clients", "action": "read"},
        {"resource": "clients", "action": "update"},
        {"resource": "clients", "action": "delete"},

        {"resource": "phones", "action": "create"},
        {"resource": "phones", "action": "read"},
        {"resource": "phones", "action": "update"},
        {"resource": "phones", "action": "delete"},

        {"resource": "address", "action": "create"},
        {"resource": "address", "action": "read"},
        {"resource": "address", "action": "update"},
        {"resource": "address", "action": "delete"},

        {"resource": "readings", "action": "create"},
        {"resource": "readings", "action": "read"},
        {"resource": "readings", "action": "update"},
        {"resource": "readings", "action": "delete"},

        {"resource": "roles", "action": "create"},
        {"resource": "roles", "action": "read"},
        {"resource": "roles", "action": "update"},
        {"resource": "roles", "action": "delete"},

        {"resource": "permissions", "action": "create"},
        {"resource": "permissions", "action": "read"},
        {"resource": "permissions", "action": "update"},
        {"resource": "permissions", "action": "delete"},

        {"resource": "meter_types", "action": "create"},
        {"resource": "meter_types", "action": "read"},
        {"resource": "meter_types", "action": "update"},
        {"resource": "meter_types", "action": "delete"},

        {"resource": "role_permissions", "action": "create"},
        {"resource": "role_permissions", "action": "read"},
        {"resource": "role_permissions", "action": "update"},
        {"resource": "role_permissions", "action": "delete"},

        {"resource": "user_roles", "action": "create"},
        {"resource": "user_roles", "action": "read"},
        {"resource": "user_roles", "action": "update"},
        {"resource": "user_roles", "action": "delete"},
    ],
    "system_manager": [
        {"resource": "users", "action": "read"},

        {"resource": "clients", "action": "create"},
        {"resource": "clients", "action": "read"},
        {"resource": "clients", "action": "update"},
        {"resource": "clients", "action": "delete"},

        {"resource": "phones", "action": "create"},
        {"resource": "phones", "action": "read"},
        {"resource": "phones", "action": "update"},
        {"resource": "phones", "action": "delete"},

        {"resource": "address", "action": "create"},
        {"resource": "address", "action": "read"},
        {"resource": "address", "action": "update"},
        {"resource": "address", "action": "delete"},

        {"resource": "readings", "action": "create"},
        {"resource": "readings", "action": "read"},
        {"resource": "readings", "action": "update"},
        {"resource": "readings", "action": "delete"},

        {"resource": "roles", "action": "read"},
        {"resource": "permissions", "action": "read"},

        {"resource": "meter_types", "action": "create"},
        {"resource": "meter_types", "action": "read"},
        {"resource": "meter_types", "action": "update"},
        {"resource": "meter_types", "action": "delete"},

        {"resource": "role_permissions", "action": "read"},
        {"resource": "user_roles", "action": "read"},
    ],
    "viewer": [
        {"resource": "users", "action": "read"},
        {"resource": "clients", "action": "read"},
        {"resource": "phones", "action": "read"},
        {"resource": "address", "action": "read"},
        {"resource": "readings", "action": "read"},
        {"resource": "roles", "action": "read"},
        {"resource": "permissions", "action": "read"},
        {"resource": "meter_types", "action": "read"},
        {"resource": "role_permissions", "action": "read"},
        {"resource": "user_roles", "action": "read"},
    ],
}


async def get_or_create_permission(session: AsyncSession, item: dict) -> Permission:
    stmt = select(Permission).where(
        Permission.resource == item["resource"],
        Permission.action == item["action"],
    )
    result = await session.execute(stmt)
    permission = result.scalar_one_or_none()

    if permission:
        return permission

    permission = Permission(**item)
    session.add(permission)
    await session.flush()
    return permission


async def get_or_create_role(session: AsyncSession, item: dict) -> Role:
    stmt = select(Role).where(Role.name == item["name"])
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()

    if role:
        return role

    role = Role(**item)
    session.add(role)
    await session.flush()
    return role


async def get_permission_by_resource_action(session: AsyncSession, resource: str, action: str) -> Permission | None:
    stmt = select(Permission).where(
        Permission.resource == resource,
        Permission.action == action,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def seed_permissions(session: AsyncSession):
    for item in PERMISSIONS_DATA:
        await get_or_create_permission(session, item)
    await session.commit()


async def seed_roles(session: AsyncSession):
    for item in ROLES_DATA:
        await get_or_create_role(session, item)
    await session.commit()


async def seed_role_permissions(session: AsyncSession):
    # Сначала получаем все роли
    roles_result = await session.execute(select(Role))
    roles = {role.name: role for role in roles_result.scalars().all()}

    for role_name, perms in ROLE_PERMISSIONS_DATA.items():
        role = roles.get(role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found in DB")

        for perm_data in perms:
            permission = await get_permission_by_resource_action(
                session,
                perm_data["resource"],
                perm_data["action"],
            )
            if not permission:
                raise ValueError(
                    f"Permission not found: {perm_data['resource']}:{perm_data['action']}"
                )

            stmt = select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                session.add(RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                ))

    await session.commit()


async def main():
    async with AsyncSessionLocal() as session:
        try:
            await seed_permissions(session)
            await seed_roles(session)
            await seed_role_permissions(session)
            print("База успешно заполнена.")
        except IntegrityError as e:
            await session.rollback()
            print("Ошибка целостности данных:", e)
        except Exception as e:
            await session.rollback()
            print("Ошибка при заполнении базы:", e)


if __name__ == "__main__":
    asyncio.run(main())
