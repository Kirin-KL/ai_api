import shutil
from datetime import datetime
from pathlib import Path
import uuid

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, status, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse
from typing_extensions import override

from db.database import get_async_db
from word_to_text import speak
from audio_to_text import audio_to_digits, audio_to_command


from typing import Optional

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Библиотека дает возможность запустить код в параллельном потоке
from starlette.concurrency import run_in_threadpool

import db.crud as db_crud
import db.models as db_models

from security import process_password, get_current_user

from shemas import ClientCreate, ClientResponse, ClientActionRequest, PhoneCreate, PhoneActionRequest, AddressCreate, \
    AddressActionRequest, TypeMeterCreate, TypeMeterActionRequest, MeterCreate, MeterActionRequest, ZoneCreate, \
    ZoneActionRequest, ReadingsCreate, ReadingsActionRequest, UserCreate, UserActionRequest, RoleCreate, \
    PermissionCreate, PermissionActionRequest, RoleActionRequest, UserRoleCreate, UserRoleActionRequest, \
    RolePermissionCreate, RolePermissionActionRequest, PhoneResponse, AddressResponse, TypeMeterResponse, MeterResponse, \
    ZoneResponse, ReadingsResponse, UserResponse, RoleResponse, PermissionResponse, RolePermissionResponse, \
    UserRoleResponse, AuditLogResponse, CreateScriptFile

from routers.authorization import router as auth_router

# --- Настройки ---
UPLOAD_DIR_DIGIT = Path("uploads_digit")
# Создаём папку если не существует
UPLOAD_DIR_DIGIT.mkdir(exist_ok=True)

UPLOAD_DIR_COMMAND = Path("uploads_command")
# Создаём папку если не существует
UPLOAD_DIR_COMMAND.mkdir(exist_ok=True)


TTS_DIR = Path("tts_dir")
TTS_DIR.mkdir(exist_ok=True)

#Расширение файлов
ALLOWED_EXTENSION = ".wav"


MODEL_MAP = {
    "clients": db_models.Client,
    "phones": db_models.Phone,
    "addresses": db_models.Address,
    "meter_types": db_models.MeterType,
    "meters": db_models.Meter,
    "zones": db_models.Zone,
    "readings": db_models.Reading,
    "users": db_models.User,
    "roles": db_models.Role,
    "permissions": db_models.Permission,
    "role_permissions": db_models.RolePermission,
    "user_roles": db_models.UserRole,
    "audit_log": db_models.AuditLog,
}

SCHEMA_MAP = {
    "clients": ClientResponse,
    "phones": PhoneResponse,
    "addresses": AddressResponse,
    "meter_types": TypeMeterResponse,
    "meters": MeterResponse,
    "zones": ZoneResponse,
    "readings": ReadingsResponse,
    "users": UserResponse,
    "roles": RoleResponse,
    "permissions": PermissionResponse,
    "role_permissions": RolePermissionResponse,
    "user_roles": UserRoleResponse,
    "audit_log": AuditLogResponse,
}


NAME_OBJECT = {
    "clients":"client",
    "phones": "phones",
    "addresses": "addresses",
    "meter_types": "meter_types",
    "meters": "meters",
    "zones": "zones",
    "readings": "readings",
    "users": "users",
    "roles": "roles",
    "permissions": "permissions",
    "role_permissions": "role_permissions",
    "user_roles": "user_roles",
}

NAME_ACTIONS = {
    "create":"create",
    "update":"update",
    "delete":"delete",
    "read":"read"
}


# Инициализация сервера
app = FastAPI(title="Api server")

security = HTTPBearer()

app.include_router(auth_router)

# Эндпоинт для получения информации о работе api
@app.get("/")
def root():
    return {
        "message": "WAV API is running",
    }


async def save_file(upload_dir, file: UploadFile = File(...)):
    """
    Функция для сохранения файла на сервере
    :param upload_dir:
    :param file:
    :return:
    """
    # Генерируем безопасное уникальное имя файла
    original_name = Path(file.filename).name
    unique_filename = f"{uuid.uuid4()}_{original_name}"

    file_path = upload_dir / unique_filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        await file.close()

    return str(file_path)


# Эндпоинт для просмотра списка файлов
@app.get("/files")
async def list_files(cred: HTTPAuthorizationCredentials = Depends(security)):
    """
    Возвращает список сохраненных WAV-файлов.
    """
    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    files_digit = []
    for file in UPLOAD_DIR_DIGIT.iterdir():
        if file.is_file() and file.suffix.lower() == ".wav":
            files_digit.append(f"{UPLOAD_DIR_DIGIT}/{file.name}")


    files_command = []
    for file in UPLOAD_DIR_COMMAND.iterdir():
        if file.is_file() and file.suffix.lower() == ".wav":
            files_command.append(f"{UPLOAD_DIR_COMMAND}/{file.name}")

    all_files = files_digit + files_command



    return {
        "files": all_files
    }


# Эндпоинт для скачивания файла
@app.get("/files/{filename}")
async def download_wav(filename: str, cred: HTTPAuthorizationCredentials = Depends(security)):
    """
    Отдает WAV-файл клиенту.
    """

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    # Защита от path traversal
    safe_filename = Path(filename).name

    possible_dirs = [UPLOAD_DIR_DIGIT, UPLOAD_DIR_COMMAND]

    for directory in possible_dirs:
        file_path = directory / safe_filename

        if file_path.exists() and file_path.is_file():
            if file_path.suffix.lower() != ".wav":
                raise HTTPException(
                    status_code=400,
                    detail="Могут быть загружены только wav файлы"
                )

            return FileResponse(
                path=file_path,
                media_type="audio/wav",
                filename=safe_filename
            )

    raise HTTPException(status_code=404, detail="Файл не найден")

@app.get("/script_files/{script_file}")
async def get_script_wav(script_file: str, cred: HTTPAuthorizationCredentials = Depends(security),):
    """
    Отдает файлы для диалога.
    """

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    file_name = {
        "start":"start.wav",
        "end":"end.wav"
    }

    filename = file_name.get(script_file)

    directory = Path("script_files")

    file_path = directory / filename

    if file_path.exists() and file_path.is_file():
        return FileResponse(
            path=file_path,
            media_type="audio/wav",
            filename=script_file
            )

    raise HTTPException(status_code=404, detail="Файл не найден")


@app.post("/script_files")
async def set_script_wav(payload:CreateScriptFile, cred: HTTPAuthorizationCredentials = Depends(security)):
    """
    Принимает текст для команды, озвучивает его и сохраняет на сервере.
    """

    file_name = payload.name_file

    current_files = ["start.wav", "end.wav"]

    if file_name not in current_files:
        HTTPException(status_code=404, detail=f"Название файла не поддерживается, доступные файлы {current_files} ")

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    filename = Path(file_name)

    directory = Path("script_files")

    file_path = directory / filename

    await run_in_threadpool(speak,payload.text_for_voice_over, file_path, overwrite = True)

    return {
        "result":f"Файл {file_name} перезаписан",
    }

# Эндпоинт для озвучки текста
@app.get("/tts/{text}")
async def tts_wav(text: str, filename: str, cred: HTTPAuthorizationCredentials = Depends(security)):
    """
    Принимает текст, озвучивает его и отдает wav-файл клиенту.
    """

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    path = Path(TTS_DIR)
    file_name = Path(f"{uuid.uuid4()}{ALLOWED_EXTENSION}")
    output_path =  path / file_name

    # оборачиваем процесс озвучки в отдельный поток, чтобы он не тормозил выполнение
    output_file_name =  await run_in_threadpool(speak,text, output_path)

    return FileResponse(
        path=output_path,
        media_type="audio/wav",
        filename=str(output_file_name)
    )


@app.post("/recognition")
async def recognize(
        cred: HTTPAuthorizationCredentials = Depends(security),
        is_recognition: str = Form(...),
        type_recognition: str = Form(...),
        file: UploadFile = File(...),):

    """
     Функция принимает настройки, ауди файл и возвращает массив распознаных цифр
    :param is_recognition:
    :param type_recognition:
    :param file:
    :return:
    """

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if type_recognition not in ["command", "digit"]:
        raise HTTPException(
            status_code=400,
            detail="type_recognition должен быть 'command' или 'digit'"
        )

    if is_recognition not in ["yes", "non"]:
        raise HTTPException(
            status_code=400,
            detail="type_recognition должен быть 'yes' или 'non'"
        )

    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только wav-файлы"
        )


    if type_recognition == "command":
        # Сохранение файла
        save_path = await save_file(UPLOAD_DIR_COMMAND, file)

        # Выход, если нет необходимости в сохранении
        if is_recognition == "non":
            return {
                "filename": file.filename,
                "type_recognition": type_recognition,
                "result": "Запись сохранена"
            }

        # Логика распознавания команд

        # Оборачиваем распознавание цифр в отдельный поток, чтобы main loop не ждал его окончания
        digit = await run_in_threadpool(audio_to_command, save_path)

        result = digit[0]


    elif type_recognition == "digit":
        # Сохранение файла
        save_path = await save_file(UPLOAD_DIR_DIGIT, file)

        # Выход, если нет необходимости в сохранении
        if is_recognition == "non":
            return {
                "filename": file.filename,
                "type_recognition": type_recognition,
                "result": "Запись сохранена"
            }

        # Логика распознавания цифр

        # Оборачиваем распознавание цифр в отдельный поток, чтобы main loop не ждал его окончания
        digit =  await run_in_threadpool(audio_to_digits,save_path)

        result = digit[0]


    return {
        "filename": file.filename,
        "type_recognition": type_recognition,
        "result": result
    }

# Эндпоинты для базы данных


@app.get("/object/{resource}")
async def get_objects(
        resource: str,
        request: Request,
        db = Depends(get_async_db),
        sort_by: Optional[str] = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        include_deleted: bool = Query(default=False),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    model = MODEL_MAP.get(resource)
    schema = SCHEMA_MAP.get(resource)
    action = NAME_ACTIONS.get("read")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    if model is None or schema is None:
        raise HTTPException(status_code=404, detail="Ресурс не найден")

    reserved_params = {"sort_by", "limit", "offset", "include_deleted"}
    filters = {
        key: value
        for key, value in request.query_params.items()
        if key not in reserved_params
    }

    objects = await db_crud.query_objects(
        db=db,
        model=model,
        filters=filters,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
        include_deleted=include_deleted,
    )

    # Если результирующий массив пуст – возвращаем 404
    if not objects:
        raise HTTPException(status_code=404, detail="Объекты не найдены")

    return [schema.model_validate(obj) for obj in objects]




@app.post("/account/{account}")
async def search_personal_account(
        account:str, db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    model = db_models.Client

    client = await db_crud.query_objects(
        db,
        model=model,
        filters={"account_number":account},
        limit=1
    )

    if not client:
        return {
            "found": False,
            "message": "Клиент с таким лицевым счётом не найден"
        }

    client = client[0]

    full_name = f"{client.last_name} {client.first_name} {client.middle_name}".strip()

    return {
        "found": True,
        "full_name": full_name,
        "client_id": client.id
    }

@app.post("/client")
async def create_client_endpoint(
        payload: ClientCreate,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("clients")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    client = await db_crud.create_client(
        db=db,
        last_name=payload.last_name,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        account_number=payload.account_number,
        changed_by=user.get("sub"),
    )

    return client


@app.post("/client/{client_id}")
async def change_client(
        client_id:int,
        payload: ClientActionRequest,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("clients")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        client = await db_crud.soft_delete_client(
            db=db,
            client_id=client_id,
            changed_by=user.get("sub"),
        )

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )

        return client

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("clients")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        client = await db_crud.update_client(
            db=db,
            client_id=client_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )

        return client

@app.post("/phone")
async def create_phone(
        payload: PhoneCreate,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("phones")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    client = await db_crud.get_by_id(db, db_models.Client, payload.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    if client.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент найден, но удален",
        )

    phone = await db_crud.create_phone(
        db=db,
        client_id=payload.client_id,
        phone_number=payload.phone_number,
        is_primary=payload.is_primary,
        changed_by=user.get("sub"),
    )

    return phone

@app.post("/phone/{phone_id}")
async def change_phone(
        phone_id:int,
        payload: PhoneActionRequest,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("phones")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        phone = await db_crud.soft_delete_phone(
            db=db,
            phone_id=phone_id,
            changed_by=user.get("sub"),
        )

        if not phone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Телефон не найден",
            )

        return phone

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("phones")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        client = await db_crud.get_by_id(db, db_models.Client, payload.client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )

        if client.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент найден, но удален",
            )

        phone = await db_crud.update_phone(
            db=db,
            phone_id=phone_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not phone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Телефон не найден",
            )

        return phone

@app.post("/address")
async def create_address(
        payload: AddressCreate,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("address")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    client = await db_crud.get_by_id(db, db_models.Client, payload.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    if client.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент найден, но удален",
        )

    address = await db_crud.create_address(
        db=db,
        client_id=payload.client_id,
        city=payload.city,
        street=payload.street,
        house=payload.house,
        flat=payload.flat,
        changed_by=user.get("sub")
    )

    return address

@app.post("/address/{address_id}")
async def change_address(
        address_id:int,
        payload: AddressActionRequest,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("address")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        address = await db_crud.soft_delete_address(
            db=db,
            address_id=address_id,
            changed_by=user.get("sub"),
        )

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Адрес не найден",
            )

        return address

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("address")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        client = await db_crud.get_by_id(db, db_models.Client, payload.client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )

        if client.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент найден, но удален",
            )

        address = await db_crud.update_address(
            db=db,
            address_id=address_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Адрес не найден",
            )

        return address


@app.post("/meter_type")
async def create_meter_type(
        payload: TypeMeterCreate,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("meter_types")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    metr_type = await db_crud.create_meter_type(
        db=db,
        name=payload.name,
        changed_by=user.get("sub")
    )

    return metr_type

@app.post("/meter_type/{meter_type_id}")
async def change_meter_type(
        meter_type_id:int,
        payload: TypeMeterActionRequest,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("meter_types")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        metr_type = await db_crud.soft_delete_meter_type(
            db=db,
            type_id=meter_type_id,
            changed_by=user.get("sub"),
        )

        if not metr_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип ПУ не найден",
            )

        return metr_type

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("meter_types")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        metr_type = await db_crud.update_meter_type(
            db=db,
            type_id=meter_type_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not metr_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Адрес не найден",
            )

        return metr_type


@app.post("/meter")
async def create_meter(
        payload: MeterCreate,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("meters")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    client = await db_crud.get_by_id(db, db_models.Client, payload.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    if client.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент найден, но удален",
        )

    meter_type = await db_crud.get_by_id(db, db_models.MeterType, payload.type_id)
    if not meter_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тип ПУ не найден",
        )
    if meter_type.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тип ПУ найден, но удален",
        )

    meter = await db_crud.create_meter(
        db=db,
        serial_number=payload.serial_number,
        name=payload.name,
        client_id=payload.client_id,
        type_id=payload.type_id,
        changed_by=user.get("sub")
    )

    return meter

@app.post("/meter/{meter_id}")
async def change_meter(
        meter_id:int,
        payload: MeterActionRequest,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("meters")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        meter = await db_crud.soft_delete_meter(
            db=db,
            meter_id=meter_id,
            changed_by=user.get("sub"),
        )

        if not meter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ПУ не найден",
            )

        return meter

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("meters")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        client = await db_crud.get_by_id(db, db_models.Client, payload.client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )
        if client.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент найден, но удален",
            )

        meter_type = await db_crud.get_by_id(db, db_models.MeterType, payload.type_id)
        if not meter_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип ПУ не найден",
            )
        if meter_type.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип ПУ найден, но удален",
            )

        meter = await db_crud.update_meter(
            db=db,
            meter_id=meter_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not meter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Адрес не найден",
            )

        return meter




@app.post("/zone")
async def create_zone(
        payload: ZoneCreate,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("zones")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    zone = await db_crud.create_zone(
        db=db,
        name=payload.name,
        description=payload.description,
        changed_by=user.get("sub")
    )

    return zone

@app.post("/zone/{zone_id}")
async def change_zone(
        zone_id:int,
        payload: ZoneActionRequest,
        db = Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("zones")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        zone = await db_crud.soft_delete_zone(
            db=db,
            zone_id=zone_id,
            changed_by=user.get("sub"),
        )

        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Зона ПУ не найдена",
            )

        return zone

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("zones")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        zone = await db_crud.update_zone(
            db=db,
            zone_id=zone_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Зона ПУ не найдена",
            )

        return zone







@app.post("/reading")
async def create_reading(
        payload: ReadingsCreate,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("readings")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    client = await db_crud.get_by_id(db, db_models.Client, payload.submitted_by)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    if client.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент найден, но удален",
        )

    meter = await db_crud.get_by_id(db, db_models.Meter, payload.meter_id)
    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ПУ не найден",
        )
    if meter.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ПУ найден, но удален",
        )

    zone = await db_crud.get_by_id(db, db_models.Zone, payload.zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Зона не найдена",
         )
    if zone.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Зона найдена, но удалена",
           )

    reading = await db_crud.create_reading(
        db=db,
        meter_id=payload.meter_id,
        zone_id=payload.zone_id,
        value=payload.value,
        date=payload.date,
        submitted_by=payload.submitted_by,
        changed_by=user.get("sub"),
    )

    return reading

@app.post("/reading/{reading_id}")
async def change_reading(
        reading_id: int,
        payload: ReadingsActionRequest,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("readings")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        reading = await db_crud.soft_delete_reading(
            db=db,
            reading_id=reading_id,
            changed_by=user.get("sub"),
        )

        if not reading:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Запись показаний не найдена",
            )

        return reading

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("readings")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        client = await db_crud.get_by_id(db, db_models.Client, payload.submitted_by)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )
        if client.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент найден, но удален",
            )

        meter = await db_crud.get_by_id(db, db_models.Meter, payload.meter_id)

        if not meter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ПУ не найден",
            )
        if meter.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ПУ найден, но удален",
            )

        zone = await db_crud.get_by_id(db, db_models.Zone, payload.zone_id)
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Зона не найдена",
            )
        if zone.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Зона найдена, но удалена",
            )

        reading = await db_crud.update_reading(
            db=db,
            reading_id=reading_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not reading:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Запись показаний не найдена",
            )

        return reading




@app.post("/user")
async def create_user(
        payload: UserCreate,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):


    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("users")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    last_login = datetime.now() # TODO: при создании пользователя не надо устанавливать last_login

    password_hash = process_password(password=payload.password_hash.strip())

    user = await db_crud.create_user(
        db=db,
        full_name=payload.full_name,
        nickname=payload.nickname,
        email=payload.email,
        password_hash=password_hash,
        last_login_at=last_login,
        changed_by=user.get("sub")
    )

    return user


@app.post("/user/{user_id}")
async def change_user(
        user_id: int,
        payload: UserActionRequest,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("users")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        user = await db_crud.soft_delete_user(
            db=db,
            user_id=user_id,
            changed_by=user.get("sub"),
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        return user

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("users")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        data["last_login_at"] = datetime.now()

        if "password_hash" in data:
            data["password_hash"] = process_password(data["password_hash"].strip())


        user = await db_crud.update_user(
            db=db,
            user_id=user_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        return user


@app.post("/role")
async def create_role(
        payload: RoleCreate,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):


    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("roles")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    role = await db_crud.create_role(
        db=db,
        name=payload.name,
        description=payload.description,
        changed_by=user.get("sub")
    )

    return role


@app.post("/role/{role_id}")
async def change_role(
        role_id: int,
        payload: RoleActionRequest,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("roles")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        role = await db_crud.soft_delete_role(
            db=db,
            role_id=role_id,
            changed_by=user.get("sub"),
        )

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Роль не найдена",
            )

        return role

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("roles")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        role = await db_crud.update_role(
            db=db,
            role_id=role_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Роль не найдена",
            )

        return role






@app.post("/permission")
async def create_permission(
        payload: PermissionCreate,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("permissions")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    role = await db_crud.create_permission(
        db=db,
        resource=payload.resource,
        action=payload.action,
        name=payload.name,
        changed_by=user.get("sub")
    )

    return role


@app.post("/permission/{permission_id}")
async def change_permission(
        permission_id: int,
        payload: PermissionActionRequest,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    token = cred.credentials
    user = get_current_user(token)

    if payload.action_type == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("permissions")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        permission = await db_crud.soft_delete_permission(
            db=db,
            permission_id=permission_id,
            changed_by=user.get("sub"),
        )

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Разрешение не найдено",
            )

        return permission

    if payload.action_type == "update":

        action = payload.action
        resource = NAME_OBJECT.get("permissions")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        permission = await db_crud.update_permission(
            db=db,
            permission_id=permission_id,
            data=data,
            changed_by=user.get("sub"),
        )

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Разрешение не найдено",
            )

        return permission




@app.post("/role_permission")
async def create_role_permission(
        payload: RolePermissionCreate,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):

    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("permissions")

    await db_crud.check_permission(db, user.get("role_id"), resource, action)

    role = await db_crud.get_by_id(db, db_models.Role, payload.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Роль не найдена",
        )
    if role.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Роль найдена, но удалена",
        )

    permission = await db_crud.get_by_id(db, db_models.Permission, payload.permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Разрешение не найдено",
        )
    if permission.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Разрешение найдено, но удалено",
        )

    role_permission = await db_crud.create_permission_to_role(
        db=db,
        role_id=payload.role_id,
        permission_id=payload.permission_id,
        changed_by=user.get("sub")
    )

    return role_permission


@app.post("/role_permission/{role_permission_id}")
async def change_role_permission(
        role_permission_id:int,
        payload: RolePermissionActionRequest,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):


    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("role_permissions")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        role_permission = await db_crud.soft_remove_permission_from_role(
            db=db,
            role_permission_id=role_permission_id,
            changed_by=user.get("sub"),
        )

        if not role_permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Запись 'роль-разрешение' не найдена",
            )

        return role_permission

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("role_permissions")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Данный метод пока не поддерживается",
        )


@app.post("/user_role")
async def create_user_role(
        payload: UserRoleCreate,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):


    # Проверка токена пользователя
    token = cred.credentials
    user_jwt = get_current_user(token)

    action = NAME_ACTIONS.get("create")
    resource = NAME_OBJECT.get("user_roles")

    await db_crud.check_permission(db, user_jwt.get("role_id"), resource, action)

    user = await db_crud.get_by_id(db, db_models.User, payload.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь найден, но удален",
        )

    role = await db_crud.get_by_id(db, db_models.Role, payload.role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Роль не найдена",
        )
    if role.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Роль найдена, но удалена",
        )

    user_role = await db_crud.create_role_to_user(
        db=db,
        role_id=payload.role_id,
        user_id=payload.user_id,
        changed_by=user_jwt.get("sub")
    )

    return user_role


@app.post("/user_role/{user_role_id}")
async def change_user_role(
        user_role_id:int,
        payload: UserRoleActionRequest,
        db=Depends(get_async_db),
        cred: HTTPAuthorizationCredentials = Depends(security)):


    # Проверка токена пользователя
    token = cred.credentials
    user = get_current_user(token)

    if payload.action == "delete":

        action = payload.action
        resource = NAME_OBJECT.get("user_roles")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        user_role = await db_crud.soft_remove_role_from_user(
            db=db,
            user_roles_id=user_role_id,
            changed_by=user.get("sub"),
        )

        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Запись 'роль-разрешение' не найдена",
            )

        return user_role

    if payload.action == "update":

        action = payload.action
        resource = NAME_OBJECT.get("user_roles")

        await db_crud.check_permission(db, user.get("role_id"), resource, action)

        data = payload.model_dump(
            exclude_unset=True,
            exclude={"action"},
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не переданы данные для обновления",
            )

        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Данный метод пока не поддерживается",
        )

