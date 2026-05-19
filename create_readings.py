import asyncio
import random
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from db.database import AsyncSessionLocal
from db.models import Client, Phone, Address, Meter, MeterType, Zone


# ==================== ГЕНЕРАЦИЯ ДАННЫХ ====================

CITY = "Речный"
STREETS = ["Алещенкова", "Ленина", "Советская", "Мира", "Гагарина",
           "Пушкина", "Лермонтова", "Кирова", "Строителей", "Юбилейная",
           "Набережная", "Заречная", "Лесная", "Парковая", "Молодежная"]
HOUSE_NUMBERS = [str(i) for i in range(1, 101)] + [f"{i}А" for i in range(1, 20)] + [f"{i}Б" for i in range(1, 10)]

METER_TYPES_DATA = [
    {"name": "горячая вода"},
    {"name": "холодная вода"},
    {"name": "электроэнергия"},
]

METER_NAMES = [
    "туалет", "санузел", "кухня", "АГАТ 2-12", "АГАТ 2-32",
    "Меркурий 230", "Нева 101", "Энергомера", "КВТ", "ИНТЕР",
    "прихожая", "коридор", "ванная", "гараж", "подвал"
]

FIRST_NAMES_MALE = ["Александр", "Дмитрий", "Михаил", "Андрей", "Владимир",
                    "Николай", "Павел", "Артем", "Виктор", "Сергей", "Алексей"]
FIRST_NAMES_FEMALE = ["Елена", "Ольга", "Татьяна", "Марина", "Ирина",
                      "Светлана", "Юлия", "Анна", "Наталья", "Екатерина"]
LAST_NAMES_MALE = ["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов",
                   "Волков", "Соколов", "Лебедев", "Козлов", "Новиков"]
LAST_NAMES_FEMALE = [name + "а" for name in LAST_NAMES_MALE]
MIDDLE_NAMES_MALE = ["Иванович", "Петрович", "Сидорович", "Андреевич", "Сергеевич",
                     "Владимирович", "Николаевич", "Алексеевич", "Михайлович", "Викторович"]
MIDDLE_NAMES_FEMALE = [name.replace("ич", "на") for name in MIDDLE_NAMES_MALE]

PHONE_OPERATORS = ["901", "902", "903", "904", "905", "906", "907", "908", "909", "910",
                   "911", "912", "913", "914", "915", "916", "917", "918", "919", "920"]


def generate_serial_number():
    prefixes = ["010", "080", "257", "690", "768", "766", "413", "907", "Т"]
    if random.choice([True, False]):
        return f"{random.choice(prefixes)} {random.randint(10000, 99999)} {random.randint(1, 99)}"
    return str(random.randint(10000000, 99999999))


def generate_phone():
    return f"+7{random.choice(PHONE_OPERATORS)}{random.randint(1000000, 9999999)}"


def generate_client_data(index: int, used_accounts: set, used_serials: set, used_phones: set):
    # Уникальный лицевой счёт
    while True:
        account = str(random.randint(1000000000, 9999999999))
        if account not in used_accounts:
            used_accounts.add(account)
            break

    is_male = random.choice([True, False])
    if is_male:
        last_name = random.choice(LAST_NAMES_MALE)
        first_name = random.choice(FIRST_NAMES_MALE)
        middle_name = random.choice(MIDDLE_NAMES_MALE)
    else:
        last_name = random.choice(LAST_NAMES_FEMALE)
        first_name = random.choice(FIRST_NAMES_FEMALE)
        middle_name = random.choice(MIDDLE_NAMES_FEMALE)

    street = random.choice(STREETS)
    house = random.choice(HOUSE_NUMBERS)
    flat = random.randint(1, 200)

    phones = []
    num_phones = random.randint(1, 2)
    for _ in range(num_phones):
        while True:
            phone = generate_phone()
            if phone not in used_phones:
                used_phones.add(phone)
                break
        phones.append({"phone_number": phone, "is_primary": len(phones) == 0})

    meters = []
    num_meters = random.randint(1, 4)
    for _ in range(num_meters):
        while True:
            serial = generate_serial_number()
            if serial not in used_serials:
                used_serials.add(serial)
                break
        meter_type = random.choice(METER_TYPES_DATA)
        meters.append({
            "serial_number": serial,
            "name": random.choice(METER_NAMES),
            "type_name": meter_type["name"]
        })

    return {
        "client": {
            "last_name": last_name,
            "first_name": first_name,
            "middle_name": middle_name,
            "account_number": account,
            "phones": phones
        },
        "address": {
            "city": CITY,
            "street": street,
            "house": house,
            "flat": str(flat)
        },
        "meters": meters
    }


def generate_all_clients(n=40):
    used_accounts = set()
    used_serials = set()
    used_phones = set()
    clients = []
    for i in range(n):
        clients.append(generate_client_data(i, used_accounts, used_serials, used_phones))
    return clients


# ==================== ЗАГРУЗКА В БД ====================

async def get_or_create_meter_type(session: AsyncSession, name: str) -> MeterType:
    stmt = select(MeterType).where(MeterType.name == name)
    result = await session.execute(stmt)
    mt = result.scalar_one_or_none()
    if mt:
        return mt
    mt = MeterType(name=name)
    session.add(mt)
    await session.flush()
    return mt


async def get_or_create_zone(session: AsyncSession, name: str, description: str = None) -> Zone:
    stmt = select(Zone).where(Zone.name == name)
    result = await session.execute(stmt)
    zone = result.scalar_one_or_none()
    if zone:
        return zone
    zone = Zone(name=name, description=description)
    session.add(zone)
    await session.flush()
    return zone


async def get_or_create_client(session: AsyncSession, data: dict) -> Client:
    # Убираем поле "phones", так как оно не является колонкой модели Client
    client_data = {k: v for k, v in data.items() if k != "phones"}
    stmt = select(Client).where(Client.account_number == client_data["account_number"])
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()
    if client:
        return client
    client = Client(**client_data)
    session.add(client)
    await session.flush()
    return client


async def get_or_create_phone(session: AsyncSession, client_id: int, data: dict) -> Phone:
    stmt = select(Phone).where(Phone.phone_number == data["phone_number"])
    result = await session.execute(stmt)
    phone = result.scalar_one_or_none()
    if phone:
        if phone.client_id != client_id:
            raise ValueError(f"Phone {data['phone_number']} belongs to another client")
        return phone
    phone = Phone(client_id=client_id, **data)
    session.add(phone)
    await session.flush()
    return phone


async def get_or_create_address(session: AsyncSession, client_id: int, data: dict) -> Address:
    stmt = select(Address).where(
        Address.client_id == client_id,
        Address.city == data["city"],
        Address.street == data["street"],
        Address.house == data["house"],
        Address.flat == data["flat"],
    )
    result = await session.execute(stmt)
    address = result.scalar_one_or_none()
    if address:
        return address
    address = Address(client_id=client_id, **data)
    session.add(address)
    await session.flush()
    return address


async def get_or_create_meter(session: AsyncSession, client_id: int, data: dict, type_id: int) -> Meter:
    stmt = select(Meter).where(Meter.serial_number == data["serial_number"])
    result = await session.execute(stmt)
    meter = result.scalar_one_or_none()
    if meter:
        if meter.client_id != client_id:
            raise ValueError(f"Meter {data['serial_number']} belongs to another client")
        return meter
    meter = Meter(
        serial_number=data["serial_number"],
        name=data["name"],
        client_id=client_id,
        type_id=type_id
    )
    session.add(meter)
    await session.flush()
    return meter


async def main():
    print("Генерация данных 40 клиентов...")
    clients_data = generate_all_clients(40)
    print(f"Сгенерировано {len(clients_data)} клиентов")

    async with AsyncSessionLocal() as session:
        try:
            print("Добавление типов ПУ и зон...")
            for mt in METER_TYPES_DATA:
                await get_or_create_meter_type(session, mt["name"])
            zones = [
                {"name": "Общая", "description": "Общая зона учета"},
                {"name": "Дневная", "description": "Дневная зона (для двухтарифных счётчиков)"},
                {"name": "Ночная", "description": "Ночная зона (для двухтарифных счётчиков)"},
            ]
            for zone in zones:
                await get_or_create_zone(session, zone["name"], zone["description"])

            # Кэш типов ПУ по имени
            meter_types = {}
            result = await session.execute(select(MeterType))
            for mt in result.scalars():
                meter_types[mt.name] = mt.id

            print("Загрузка клиентов, адресов, телефонов и приборов учёта...")
            for client_item in clients_data:
                client = await get_or_create_client(session, client_item["client"])
                await get_or_create_address(session, client.id, client_item["address"])
                for phone_data in client_item["client"]["phones"]:
                    await get_or_create_phone(session, client.id, phone_data)
                for meter_data in client_item["meters"]:
                    type_id = meter_types.get(meter_data["type_name"])
                    if type_id is None:
                        raise ValueError(f"Неизвестный тип ПУ: {meter_data['type_name']}")
                    await get_or_create_meter(session, client.id, meter_data, type_id)

            await session.commit()
            print(f"✅ База данных успешно заполнена! Добавлено клиентов: {len(clients_data)}")

        except IntegrityError as e:
            await session.rollback()
            print("❌ Ошибка целостности данных:", e)
        except Exception as e:
            await session.rollback()
            print("❌ Ошибка при загрузке:", e)


if __name__ == "__main__":
    asyncio.run(main())