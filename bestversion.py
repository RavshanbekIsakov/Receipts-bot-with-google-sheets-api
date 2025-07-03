from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime
import asyncio

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

API_TOKEN = '7683442068:AAHzm3u_-AhX2SnQK2QR0iSPPJEhsW5QwJM'
GROUP_CHAT_ID = -1002103077769
SHEET_NAME = "Fleet"
PARTS_SHEET_NAME = "Parts"
CREDENTIALS_FILE = "credentials.json"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class RepairForm(StatesGroup):
    header = State()
    trailer = State()
    repair_target = State()
    part_selection = State()
    add_new_part = State()
    ask_new_part_type = State()
    action_selection = State()
    date = State()
    payer = State()
    payment_method = State()
    card_digits = State()
    other_method = State()
    cost = State()
    receipt = State()
    notes = State()

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1
parts_sheet = client.open(SHEET_NAME).worksheet(PARTS_SHEET_NAME)

def get_parts(part_type):
    all_parts = parts_sheet.get_all_values()
    return [row[0] for row in all_parts if row[1] == part_type]

def add_part(part_name, part_type):
    parts_sheet.append_row([part_name, part_type])

def write_to_google_sheets(data):
    try:
        row = [
            data['header'],
            data['trailer'],
            data['repair_target'],
            ", ".join(data['repairs']),
            data['date'],
            data['payer'],
            data['payment_method'],
            data['cost'],
            data['notes'],
            data['author']
        ]
        sheet.append_row(row)
    except Exception as e:
        print(f"[Google Sheets ERROR]: {e}")

ACTIONS = ["Replace", "Check", "Buy", "Repair", "Patch"]

@dp.message(F.text.startswith("/add"))
async def cmd_add(message: Message, state: FSMContext):
    header = message.text[5:].strip()
    await state.set_state(RepairForm.trailer)
    await state.update_data(header=header, author=message.from_user.username, repairs=[])
    await message.answer("Введите номер трейлера (если нет — напишите '-' или 'нет'):")

@dp.message(RepairForm.trailer)
async def get_trailer(message: Message, state: FSMContext):
    await state.update_data(trailer=message.text)
    await state.set_state(RepairForm.repair_target)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Truck")], [KeyboardButton(text="Trailer")], [KeyboardButton(text="Both")]],
        resize_keyboard=True
    )
    await message.answer("Что именно ремонтировали?", reply_markup=keyboard)

@dp.message(RepairForm.repair_target)
async def get_repair_target(message: Message, state: FSMContext):
    target = message.text
    await state.update_data(repair_target=target)
    await state.set_state(RepairForm.part_selection)
    await show_parts(message, target)

async def show_parts(message: Message, target):
    parts = get_parts("Truck") if target == "Truck" else get_parts("Trailer") if target == "Trailer" else get_parts("Truck") + get_parts("Trailer")
    keyboard = [[KeyboardButton(text=p)] for p in parts]
    if target != "Both":
        keyboard.append([KeyboardButton(text="➕ Добавить часть")])
    keyboard.append([KeyboardButton(text="✅ Завершить выбор ремонта")])
    await message.answer("Выберите часть или добавьте новую:", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True))

@dp.message(RepairForm.part_selection)
async def part_chosen(message: Message, state: FSMContext):
    text = message.text
    if text == "➕ Добавить часть":
        data = await state.get_data()
        if data['repair_target'] == "Both":
            await state.set_state(RepairForm.ask_new_part_type)
            await message.answer("Для какой части транспорта эта новая часть? (Truck/Trailer)")
        else:
            await state.set_state(RepairForm.add_new_part)
            await message.answer("Введите название новой части:")
    elif text == "✅ Завершить выбор ремонта":
        await state.set_state(RepairForm.date)
        await message.answer("Введите дату ремонта (в формате YYYY-MM-DD):", reply_markup=ReplyKeyboardRemove())
    else:
        await state.update_data(current_part=text)
        await state.set_state(RepairForm.action_selection)
        keyboard = [[KeyboardButton(text=a)] for a in ACTIONS]
        await message.answer(f"Вы выбрали: {text}. Теперь выберите действие:", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True))

@dp.message(RepairForm.ask_new_part_type)
async def ask_part_type(message: Message, state: FSMContext):
    if message.text not in ["Truck", "Trailer"]:
        await message.answer("Введите Truck или Trailer")
        return
    await state.update_data(new_part_type=message.text)
    await state.set_state(RepairForm.add_new_part)
    await message.answer("Введите название новой части:")

@dp.message(RepairForm.add_new_part)
async def add_part_handler(message: Message, state: FSMContext):
    part_name = message.text.strip()
    data = await state.get_data()
    part_type = data.get("new_part_type", data.get("repair_target"))
    add_part(part_name, part_type)
    await state.set_state(RepairForm.part_selection)
    await show_parts(message, part_type)

@dp.message(RepairForm.action_selection)
async def action_chosen(message: Message, state: FSMContext):
    action = message.text
    data = await state.get_data()
    repair = f"{action} {data['current_part']}"
    repairs = data.get("repairs", [])
    repairs.append(repair)
    await state.update_data(repairs=repairs)
    await state.set_state(RepairForm.part_selection)
    await show_parts(message, data['repair_target'])

@dp.message(RepairForm.date)
async def get_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    payer_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=option)] for option in ["Company pays", "Driver pays", "Broker pays", "Will be taken from load"]],
        resize_keyboard=True
    )
    await state.set_state(RepairForm.payer)
    await message.answer("Кто оплатил ремонт?", reply_markup=payer_keyboard)

@dp.message(RepairForm.payer)
async def get_payer(message: Message, state: FSMContext):
    await state.update_data(payer=message.text)
    method_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=m)] for m in ["Zelle", "By card over the phone", "Physical card (driver paid)", "EFS code", "Love's/TA account", "Other"]],
        resize_keyboard=True
    )
    await state.set_state(RepairForm.payment_method)
    await message.answer("Выберите метод оплаты:", reply_markup=method_keyboard)

@dp.message(RepairForm.payment_method)
async def select_payment_method(message: Message, state: FSMContext):
    method = message.text.strip()
    await state.update_data(payment_method=method)
    if method == "By card over the phone":
        await state.set_state(RepairForm.card_digits)
        await message.answer("Введите последние 4 цифры карты:")
    elif method == "Other":
        await state.set_state(RepairForm.other_method)
        await message.answer("Введите название метода оплаты:")
    else:
        await state.set_state(RepairForm.cost)
        await message.answer("Введите общую сумму ремонта:")

@dp.message(RepairForm.card_digits)
async def get_card_digits(message: Message, state: FSMContext):
    digits = message.text.strip()
    await state.update_data(payment_method=f"By card {digits}")
    await state.set_state(RepairForm.cost)
    await message.answer("Введите общую сумму ремонта:")

@dp.message(RepairForm.other_method)
async def get_other_method(message: Message, state: FSMContext):
    await state.update_data(payment_method=message.text.strip())
    await state.set_state(RepairForm.cost)
    await message.answer("Введите общую сумму ремонта:")

@dp.message(RepairForm.cost)
async def get_cost(message: Message, state: FSMContext):
    raw = message.text.strip().replace("$", "")
    try:
        value = float(raw)
        await state.update_data(cost=f"${value:.2f}")
        await state.set_state(RepairForm.receipt)
        await message.answer("Отправьте чек (фото или файл):", reply_markup=ReplyKeyboardRemove())
    except ValueError:
        await message.answer("❌ Неверный формат. Введите сумму типа 250 или 250.00")

@dp.message(RepairForm.receipt, F.content_type.in_(["photo", "document"]))
async def get_receipt(message: Message, state: FSMContext):
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    else:
        file_id = message.document.file_id
        file_type = "document"

    await state.update_data(receipt=file_id, receipt_type=file_type)
    await state.set_state(RepairForm.notes)
    await message.answer("Есть какие-либо заметки? (если нет — напишите '-')")

@dp.message(RepairForm.notes)
async def get_notes(message: Message, state: FSMContext):
    await state.update_data(notes=message.text)
    data = await state.get_data()

    post = (
        f"{data['header']}\n\n"
        f"Trailer number: {data['trailer']}\n"
        f"Type: {data['repair_target']}\n"
        f"Repairs: {', '.join(data['repairs'])}\n"
        f"Repair date: {data['date']}\n"
        f"{data['payer']}\n"
        f"Payment method: {data['payment_method']}\n"
        f"Total cost: {data['cost']}\n"
        f"Notes: {data['notes']}\n"
        f"Done by: @{data['author']}"
    )

    if data.get("receipt_type") == "photo":
        await bot.send_photo(GROUP_CHAT_ID, photo=data['receipt'], caption=post)
    else:
        await bot.send_document(GROUP_CHAT_ID, document=data['receipt'], caption=post)

    write_to_google_sheets(data)
    await message.answer("✅ Пост отправлен в группу и сохранён в Google Sheets!", reply_markup=ReplyKeyboardRemove())
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
