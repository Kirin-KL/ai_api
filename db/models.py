from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text,
    UniqueConstraint, JSON, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


# ===========================
# 1. Клиент
# ===========================
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    last_name = Column(String)
    first_name = Column(String)
    middle_name = Column(String)
    account_number = Column(String, unique=True)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())

    phones = relationship("Phone", back_populates="client")
    addresses = relationship("Address", back_populates="client")
    meters = relationship("Meter", back_populates="client")


# ===========================
# 2. Телефоны
# ===========================
class Phone(Base):
    __tablename__ = "phones"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    phone_number = Column(String, unique=True)
    is_primary = Column(Boolean, default=False)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("Client", back_populates="phones")


# ===========================
# 3. Адреса
# ===========================
class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    city = Column(String)
    street = Column(String)
    house = Column(String)
    flat = Column(String)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("Client", back_populates="addresses")


# ===========================
# 4. Типы ПУ
# ===========================
class MeterType(Base):
    __tablename__ = "meter_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())


# ===========================
# 5. ПУ
# ===========================
class Meter(Base):
    __tablename__ = "meters"

    id = Column(Integer, primary_key=True)
    serial_number = Column(String, unique=True)
    name = Column(String)

    client_id = Column(Integer, ForeignKey("clients.id"))
    type_id = Column(Integer, ForeignKey("meter_types.id"))

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("Client", back_populates="meters")
    type = relationship("MeterType")
    readings = relationship("Reading", back_populates="meter")


# ===========================
# 6. Зоны
# ===========================
class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(Text)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())


# ===========================
# 7. Показания
# ===========================
class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True)
    meter_id = Column(Integer, ForeignKey("meters.id"))
    zone_id = Column(Integer, ForeignKey("zones.id"))
    value = Column(Numeric(15, 3))
    date = Column(DateTime(timezone=True))
    submitted_by = Column(Integer, ForeignKey("clients.id"))

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())

    meter = relationship("Meter", back_populates="readings")
    zone = relationship("Zone")
    user = relationship("Client")

    __table_args__ = (
        UniqueConstraint("meter_id", "zone_id", "date"),
    )


# ===========================
# 8. Пользователь
# ===========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String)
    nickname = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)
    last_login_at = Column(DateTime(timezone=True))

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())


# ===========================
# 9. Роли
# ===========================
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(Text)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())


# ===========================
# 10. Разрешения
# ===========================
class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    resource = Column(String)
    action = Column(String)
    name = Column(String, unique=True)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("resource", "action"),
    )


# ===========================
# 11. role_permissions
# ===========================
class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 3. Ограничение: пара (role_id, permission_id) должна быть уникальной
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )


# ===========================
# 12. user_roles
# ===========================
class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    changed_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 3. Делаем связку пользователя и роли уникальной, чтобы нельзя было выдать одну роль дважды
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )


# ===========================
# 13. Аудит лог
# ===========================
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    table_name = Column(String)
    record_id = Column(Integer)
    action = Column(String)
    old_data = Column(JSON)
    new_data = Column(JSON)
    changed_by = Column(Integer, ForeignKey("users.id"))
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

