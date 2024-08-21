from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import os
from datetime import datetime

from config import API_TOKEN

WORK_LOCATION = (41.32346500754505, 69.28690575802068)  # Ishxona koordinatalari

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Ro'yxatdan o'tgan foydalanuvchilarni saqlash
registered_users = {}
user_locations = {}

# FSM uchun holatlar
class RegisterState(StatesGroup):
    waiting_for_name = State()

class LocationState(StatesGroup):
    waiting_for_category = State()
    waiting_for_location = State()

# 1. Start
@dp.message_handler(commands=['start'])
async def register(message: types.Message):
    user_id = message.from_user.id

    if user_id in registered_users:
        await message.answer(f"Siz allaqachon ro'yxatdan o'tgansiz, {registered_users[user_id]}!")
        await ask_category(message)  # 1.2 Kategoriyani tanlash
    else:
        await message.answer("Iltimos, ismingiz va familiyangizni kiriting:")
        await RegisterState.waiting_for_name.set()

# 1.1 Foydalanuvchi ma'lumotlarini qabul qilish
@dp.message_handler(state=RegisterState.waiting_for_name, content_types=types.ContentTypes.TEXT)
async def register_user(message: types.Message, state: FSMContext):
    full_name = message.text
    user_id = message.from_user.id
    registered_users[user_id] = full_name
    await message.answer(f"Ro'yxatdan o'tdingiz, {full_name}!")
    await state.finish()  # FSMni yakunlash

    await ask_category(message)  # 1.2 Kategoriyani tanlash

    # 3. Takrorlanish
    scheduler.add_job(ask_category_scheduled, 'cron', hour=9, args=[user_id])
    scheduler.add_job(ask_category_scheduled, 'cron', hour=13, args=[user_id])
    scheduler.add_job(ask_category_scheduled, 'cron', hour=18, args=[user_id])

# 2. Kategoriyani so'rash funksiyasi
async def ask_category(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["At Work", "Not at Work", "Reasons", "In the object"]
    keyboard.add(*buttons)
    await message.answer("Qaysi holatda ekanligingizni tanlang:", reply_markup=keyboard)
    await LocationState.waiting_for_category.set()

# 2.1 Belgilangan vaqtlarda kategoriya so'rash uchun yordamchi funksiya
async def ask_category_scheduled(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["At Work", "Not at Work", "Reasons", "In the object"]
    keyboard.add(*buttons)
    await bot.send_message(user_id, "Qaysi holatda ekanligingizni tanlang:", reply_markup=keyboard)
    await LocationState.waiting_for_category.set()


# 2.2 Foydalanuvchi kategoriyani tanlaganda
@dp.message_handler(state=LocationState.waiting_for_category, content_types=types.ContentTypes.TEXT)
async def handle_category(message: types.Message, state: FSMContext):
    category = message.text
    user_id = message.from_user.id

    if category not in ["At Work", "Not at Work", "Reasons", "In the object"]:
        await message.answer("Iltimos, tugmalardan birini tanlang.")
        return

    await state.update_data(selected_category=category)

    # Har qanday kategoriya uchun lokatsiya so'rash
    await message.answer("Iltimos, lokatsiyangizni yuboring:", reply_markup=types.ReplyKeyboardRemove())
    await LocationState.waiting_for_location.set()

# 2.2 Lokatsiyani qabul qilish va tekshirish
@dp.message_handler(state=LocationState.waiting_for_location, content_types=['location'])
async def handle_location(message: types.Message, state: FSMContext):
    user_location = (message.location.latitude, message.location.longitude)
    user_id = message.from_user.id
    data = await state.get_data()
    category = data.get('selected_category')

    # Agar kategoriya "At Work" yoki "Not at Work" bo'lsa, lokatsiya tekshiriladi
    if category in ["At Work", "Not at Work"]:
        distance = calculate_distance(user_location, WORK_LOCATION)
        if distance < 0.1:  # 100 metrdan yaqin bo'lsa
            await message.answer(f"Siz ishxonadasiz ({category}). Rahmat!")
        else:
            await message.answer(f"Siz ishxonada emassiz ({category})!")

    # Har qanday holatda, lokatsiya va vaqt saqlanadi
    user_locations[user_id] = {
        'category': category,
        'location': user_location,
        'time': datetime.now()
    }

    await state.finish()
    await ask_category(message)  # 4. Kategoriya qayta chiqishi

# Masofa hisoblash funksiyasi
def calculate_distance(loc1, loc2):
    from geopy.distance import geodesic
    return geodesic(loc1, loc2).km

# Schedulerni boshlash
scheduler = AsyncIOScheduler()
scheduler.start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
