from config import API_TOKEN
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging
from geopy.distance import geodesic



ADMIN_ID = 1486580350
WORK_LOCATION = (41.30278475883332, 69.31477190655004)  # Update with actual coordinates
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Initialize database connection
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

# Create users table if it doesn't exist
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

# Close the database connection for now
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

    # Check if the user is already registered
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM users WHERE telegram_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        await message.answer(f"Вы уже зарегистрированы, {user[0]} {user[1]}!")
        if is_user_approved(user_id):
            await ask_category(message)  # 3. Category selection
    else:
        await message.answer("Пожалуйста, введите ваше имя и фамилию:")
        await RegisterState.waiting_for_name.set()


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

    # Insert the user information into the database
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (telegram_id, first_name, last_name) VALUES (?, ?, ?)',
                   (user_id, first_name, last_name))
    conn.commit()
    conn.close()

    await message.answer(f"Вы зарегистрировались, {first_name} {last_name}!\nПодождите разрешения администратора...")
    await state.finish()

    await ask_admin_approval(user_id, first_name, last_name)


# 2. Admin approval request
async def ask_admin_approval(user_id, first_name, last_name):
    # Inline keyboard for admin approval
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

# Imports and initialization code remain unchanged

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

    if category not in ["На работе", "Ушел с работы", "Отпроситься", "На объекте"]:
        await message.answer("Пожалуйста, выберите одну из кнопок.")
        return

    if category == "Отпроситься":
        # Show new buttons for "Reasons"
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = ["Отпроситься", "Болезнь"]
        keyboard.add(*buttons)
        await message.answer("Выберите причину:", reply_markup=keyboard)
        await state.finish()
        return

    await state.update_data(selected_category=category)
    await message.answer("Пожалуйста, пришлите свое местоположение:", reply_markup=types.ReplyKeyboardRemove())
    await LocationState.waiting_for_location.set()

# 5. Handle location input and verification (remains unchanged)

# New handler for "Reasons" sub-buttons
@dp.message_handler(lambda message: message.text in ["Отпроситься", "Болезнь"])
async def handle_reason_buttons(message: types.Message):
    reason = message.text
    print(f"User selected reason: {reason}")
    await ask_category(message)

# 6. Handle location input and verification
@dp.message_handler(state=LocationState.waiting_for_location, content_types=['location'])
async def handle_location(message: types.Message, state: FSMContext):
    user_location = (message.location.latitude, message.location.longitude)
    user_id = message.from_user.id
    data = await state.get_data()
    category = data.get('selected_category')

    # If the category is "At Work" or "Not at Work", verify location
    if category in ['На работе', 'Ушел с работы']:
        distance = calculate_distance(user_location, WORK_LOCATION)
        if distance < 0.1:  # Within 100 meters
            print(6.1)
            if category == 'На работе':
                await message.answer(f"Вы на работе")
            elif category == 'Ушел с работы':
                await message.answer(f"Вы ушли с работы")
        else:
            print(6.2)
            await message.answer(f"Вы не на работе!")

    # Save location and time for all categories
    save_user_location(user_id, category, user_location)

    await state.finish()
    await ask_category(message)  # Prompt category selection again


# Utility function to calculate distance between two locations
def calculate_distance(loc1, loc2):
    return geodesic(loc1, loc2).km


# Utility function to save user location and timestamp
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


# Create user_locations table if it doesn't exist
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

# Scheduler to prompt category selection at specific times
scheduler = AsyncIOScheduler()
scheduler.start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
