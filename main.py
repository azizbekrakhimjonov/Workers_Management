from config import API_TOKEN
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging
from geopy.distance import geodesic

from append import *

ADMIN_ID = 1486580350
WORK_LOCATION = (41.30278475883332, 69.31477190655004)
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    first_name TEXT,
    last_name TEXT,
    is_approved INTEGER DEFAULT 0
)
''')
conn.commit()
conn.close()


# States for FSM
class RegisterState(StatesGroup):
    waiting_for_name = State()


class LocationState(StatesGroup):
    waiting_for_category = State()
    waiting_for_location = State()


# 1. Start command handler
@dp.message_handler(commands=['start'])
async def register(message: types.Message):
    user_id = message.from_user.id

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user_id != ADMIN_ID:
        if user:
            await message.answer(f"Вы уже зарегистрированы, {user[0]} {user[1]}!")
            if is_user_approved(user_id):
                await ask_category(message)  # 3. Category selection
        else:
            await message.answer("Пожалуйста, введите ваше имя и фамилию:")
            await RegisterState.waiting_for_name.set()
            if user:
                await message.answer(f"Вы уже зарегистрированы, {user[0]} {user[1]}!")
                if is_user_approved(user_id):
                    await ask_category(message)  # 3. Category selection
    else:
        await message.answer("Вы в настоящее время являетесь администратором!", reply_markup=ReplyKeyboardRemove())


# 1.1 User registration handler
@dp.message_handler(state=RegisterState.waiting_for_name, content_types=types.ContentTypes.TEXT)
async def register_user(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    name_parts = full_name.split(maxsplit=1)

    if len(name_parts) < 2:
        await message.answer("Пожалуйста, введите ваше имя и фамилию\nНапример: Азизбек Рахимжонов.")
        return

    first_name, last_name = name_parts
    user_id = message.from_user.id

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (telegram_id, first_name, last_name) VALUES (?, ?, ?)',
                   (user_id, first_name, last_name))
    register_gs(user_id, full_name)
    conn.commit()
    conn.close()

    await message.answer(f"Вы зарегистрировались, {first_name} {last_name}!\nПодождите разрешения администратора...")
    await state.finish()

    await ask_admin_approval(user_id, first_name, last_name)


# 2. Admin approval request
async def ask_admin_approval(user_id, first_name, last_name):
    keyboard = InlineKeyboardMarkup()
    approve_button = InlineKeyboardButton("Ruxsat berish", callback_data=f"approve_{user_id}")
    deny_button = InlineKeyboardButton("Rad etish", callback_data=f"deny_{user_id}")
    keyboard.add(approve_button, deny_button)

    await bot.send_message(ADMIN_ID, f"Пользователь {first_name} {last_name} запрашивает разрешение.",
                           reply_markup=keyboard)

# 2.1 Handle admin approval or denial
@dp.callback_query_handler(lambda c: c.data.startswith('approve_') or c.data.startswith('deny_'))
async def process_admin_approval(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    action = callback_query.data.split('_')[0]

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    if action == 'approve':
        cursor.execute('UPDATE users SET is_approved = 1 WHERE telegram_id = ?', (user_id,))
        await bot.send_message(user_id, "Вам разрешено. Пожалуйста, перезапустите бота:\n /start")

    elif action == 'deny':
        cursor.execute('DELETE FROM users WHERE telegram_id = ?', (user_id,))
        await bot.send_message(user_id, "Ваше разрешение отклонено.")

    conn.commit()
    conn.close()

    await callback_query.answer()


# 3. Category selection prompt
async def ask_category(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["На работе", "Ушел с работы", "Отпроситься", "На объекте"]
    keyboard.add(*buttons)
    await message.answer("Пожалуйста, выберите одну из кнопок.", reply_markup=keyboard)
    await LocationState.waiting_for_category.set()


# 4. Handle category selection
@dp.message_handler(state=LocationState.waiting_for_category, content_types=types.ContentTypes.TEXT)
async def handle_category(message: types.Message, state: FSMContext):
    category = message.text
    user_id = message.from_user.id

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if category not in ["На работе", "Ушел с работы", "Отпроситься", "На объекте"]:
        await message.answer("Пожалуйста, выберите одну из кнопок.")
        print('На объекте')
        return

    if category == "Отпроситься":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Отпрoситься", "Болезнь"]
        keyboard.add(*buttons)
        await message.answer("Выберите причину:", reply_markup=keyboard)
        await state.finish()

        return

    await state.update_data(selected_category=category)
    await message.answer("Пожалуйста, пришлите свое местоположение:", reply_markup=types.ReplyKeyboardRemove())
    await LocationState.waiting_for_location.set()


# 5. Handle location input and verification (remains unchanged)

@dp.message_handler(lambda message: message.text in ["Отпрoситься", "Болезнь"])
async def handle_reason_buttons(message: types.Message):
    reason = message.text
    print(f"User selected reason: {reason}")

    user_id = message.from_user.id

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    # def add_gs(id, fullname, become, reason, inobject, location):
    add_gs(user_id, f"{user[0]} {user[1]}", datetime.now().strftime("%H:%M:%S"), reason, "*", "*", 0)
    await ask_category(message)


# 6. Handle location input and verification
@dp.message_handler(state=LocationState.waiting_for_location, content_types=['location'])
async def handle_location(message: types.Message, state: FSMContext):
    user_location = (message.location.latitude, message.location.longitude)
    user_id = message.from_user.id
    data = await state.get_data()
    category = data.get('selected_category')
    user_id = message.from_user.id

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if category in ['На работе', 'Ушел с работы']:
        distance = calculate_distance(user_location, WORK_LOCATION)
        if distance < 0.1:  # Within 100 meters
            print(6.1)
            date = datetime.now().strftime("%H:%M:%S")
            if category == 'На работе':
                await message.answer(f"Вы на работе")
                # add_gs(user_id, f"{user[0]} {user[1]}", datetime.now().strftime("%H:%M:%S"), "*", "*", "На работе", "=C:C-workers!D:D")
                # add_gs(user_id, f"{user[0]} {user[1]}", datetime.now().strftime("%H:%M:%S"), "*", "*", "На работе", "=VLOOKUP(A2; workers!A:D; 4; FALSE)")
                add_gs(user_id, f"{user[0]} {user[1]}", date, "*", "*", "На работе", 0)

            elif category == 'Ушел с работы':
                await message.answer(f"Вы ушли с работы")
        else:
            print(6.2)
            await message.answer(f"Вы не на работе!")
            add_gs(user_id, f"{user[0]} {user[1]}", datetime.now().strftime("%H:%M:%S"), "*", "*", "Не На работе", 0)
    elif category in ['На объекте']:
        add_gs(user_id, f"{user[0]} {user[1]}", datetime.now().strftime("%H:%M:%S"), "*", "На объекте", f"{user_location}", 0)

    save_user_location(user_id, category, user_location)

    await state.finish()
    await ask_category(message)


def calculate_distance(loc1, loc2):
    return geodesic(loc1, loc2).km


def save_user_location(user_id, category, location):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO user_locations (telegram_id, category, latitude, longitude, timestamp)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, category, location[0], location[1], datetime.now()))
    conn.commit()
    conn.close()


# Utility function to check if the user is approved
def is_user_approved(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_approved FROM users WHERE telegram_id = ?', (user_id,))
    is_approved = cursor.fetchone()
    conn.close()
    return is_approved and is_approved[0] == 1


conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    category TEXT,
    latitude REAL,
    longitude REAL,
    timestamp DATETIME
)
''')
conn.commit()
conn.close()

scheduler = AsyncIOScheduler()
scheduler.start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
