from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal, Any
from datetime import datetime


class ClientCreate(BaseModel):
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    account_number: str

class ClientActionRequest(BaseModel):
    action: Literal["update", "delete"]

    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    account_number: Optional[str] = None

class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    account_number: str

    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None




class PhoneCreate(BaseModel):
    client_id: int
    phone_number: str
    is_primary: bool = False

class PhoneActionRequest(BaseModel):
    action: Literal["update", "delete"]

    client_id: Optional[int] = None
    phone_number: Optional[str] = None
    is_primary: Optional[bool] = None

class PhoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    phone_number: str
    is_primary: bool
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None




class AddressCreate(BaseModel):
    client_id: int
    city: str
    street: str
    house: str
    flat: str

class AddressActionRequest(BaseModel):
    action: Literal["update", "delete"]

    client_id: int
    city: str
    street: str
    house: str
    flat: str

class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    city: str
    street: str
    house: str
    flat: str
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None




class TypeMeterCreate(BaseModel):
    name:str

class TypeMeterActionRequest(BaseModel):
    action: Literal["update", "delete"]

    name: str

class TypeMeterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None




class MeterCreate(BaseModel):
    serial_number:str
    name:str
    client_id:int
    type_id:int

class MeterActionRequest(BaseModel):
    action: Literal["update", "delete"]

    serial_number:str
    name:str
    client_id:int
    type_id:int

class MeterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    serial_number: str
    name: str
    client_id: int
    type_id: int
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None




class ZoneCreate(BaseModel):
    name:str
    description:str

class ZoneActionRequest(BaseModel):
    action: Literal["update", "delete"]

    name: str
    description: str

class ZoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None




class ReadingsCreate(BaseModel):
    meter_id:int
    zone_id:int
    value:int
    date:datetime
    submitted_by:int

class ReadingsActionRequest(BaseModel):
    action: Literal["update", "delete"]

    meter_id: int
    zone_id: int
    value: int
    date: datetime
    submitted_by: int

class ReadingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meter_id: int
    zone_id: int
    value: int
    date: datetime
    submitted_by: int
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None





class UserCreate(BaseModel):
    full_name:str
    nickname:str
    email:str
    password_hash:str

class UserActionRequest(BaseModel):
    action: Literal["update", "delete"]

    full_name: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    full_name: str
    nickname: str
    email: str
    password_hash: str
    last_login_at: datetime
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None


class RoleCreate(BaseModel):
    name:str
    description:str


class RoleActionRequest(BaseModel):
    action: Literal["update", "delete"]

    id:int
    name: str
    description: str


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    name: str
    description: str
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None




class PermissionCreate(BaseModel):
    resource:str
    action:str
    name:str


class PermissionActionRequest(BaseModel):
    action_type: Literal["update", "delete"]

    resource: str
    action: str
    name: str


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    resource: str
    action: str
    name: str
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None





class RolePermissionCreate(BaseModel):
    permission_id: int
    role_id: int

class RolePermissionActionRequest(BaseModel):
    action: Literal["update", "delete"]

    # permission_id: int
    # role_id: int

class RolePermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    permission_id: int
    role_id: int
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None





class UserRoleCreate(BaseModel):
    user_id: int
    role_id: int


class UserRoleActionRequest(BaseModel):
    action: Literal["update", "delete"]

    # user_id: int
    # role_id: int


class UserRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    user_id: int
    role_id: int
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    changed_at: Optional[datetime] = None




class Auth(BaseModel):
    user_login: str
    user_pass: str





class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    table_name: str
    record_id: int
    action: str
    old_data: Any | None = None
    new_data: Any | None = None
    changed_by: int | None = None
    changed_at: datetime


class CreateScriptFile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name_file:str
    text_for_voice_over: str
