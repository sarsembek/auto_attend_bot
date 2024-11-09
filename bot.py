import os
import subprocess
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from db import init_db, save_user_credentials, get_user_credentials, update_default_duration

# Загрузка переменных окружения из .env файла
load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Инициализация базы данных
init_db()

# Хранение процесса Selenium
selenium_processes = {}

# Создаем кнопки
buttons = [
    KeyboardButton(text="Запустить"),  # Кнопка для запуска скрипта по умолчанию
    KeyboardButton(text="Изменить продолжительность")
]
main_keyboard = ReplyKeyboardMarkup(keyboard=[[button] for button in buttons], resize_keyboard=True)

# Кнопка "Отмена"
cancel_button = KeyboardButton(text="Отмена")
cancel_keyboard = ReplyKeyboardMarkup(keyboard=[[cancel_button]], resize_keyboard=True)

# Состояния для Finite State Machine (FSM)
class UserInputStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_duration = State()

# Команда /start
@dp.message(Command(commands=["start"]))
async def start_command(message: types.Message, state: FSMContext):
    await message.reply("Введите ваше имя пользователя:")
    await state.set_state(UserInputStates.waiting_for_username)

# Обработка имени пользователя
@dp.message(UserInputStates.waiting_for_username)
async def get_username(message: types.Message, state: FSMContext):
    username = message.text
    await state.update_data(username=username)
    await message.reply("Теперь введите ваш пароль:")
    await state.set_state(UserInputStates.waiting_for_password)

# Обработка пароля
@dp.message(UserInputStates.waiting_for_password)
async def get_password(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    password = message.text
    user_data = await state.get_data()
    username = user_data.get("username")

    # Сохранение данных в базе данных
    save_user_credentials(user_id, username, password)

    await message.reply("Ваши данные сохранены! Теперь вы можете использовать команду /run или нажать 'Запустить'.", reply_markup=main_keyboard)
    await state.clear()

# Команда /run для запуска скрипта по умолчанию
@dp.message(Command(commands=["run"]))
async def run_default_script(message: types.Message):
    await launch_script(message)

# Обработка кнопки "Запустить"
@dp.message(lambda message: message.text == "Запустить")
async def handle_run_button(message: types.Message):
    await launch_script(message)

# Функция для запуска скрипта
async def launch_script(message: types.Message):
    user_id = message.from_user.id
    if user_credentials := get_user_credentials(user_id):
        username, password, default_duration = user_credentials
        await message.reply(f"Запускаем авто отметку с продолжительностью {default_duration} минут. Ждите...", reply_markup=cancel_keyboard)
        try:
            # Запуск процесса Selenium
            process = subprocess.Popen([
                "python", "auto_attend.py", 
                username, password, 
                str(default_duration), 
                str(message.from_user.id), 
                os.getenv("API_TOKEN")
            ])

            selenium_processes[user_id] = process
        except Exception as e:
            await message.reply(f"Ошибка при запуске: {e}", reply_markup=main_keyboard)
    else:
        await message.reply("Пожалуйста, сначала сохраните ваши учетные данные через /start.")

# Обработка кнопки "Отмена"
@dp.message(lambda message: message.text == "Отмена")
async def handle_cancel_button(message: types.Message):
    user_id = message.from_user.id
    if user_id in selenium_processes:
        process = selenium_processes[user_id]
        process.terminate()
        process.wait()  # Ждем завершения процесса
        del selenium_processes[user_id]
        await message.reply("Процесс отметки был успешно остановлен.", reply_markup=main_keyboard)
    else:
        await message.reply("Нет активного процесса для остановки.", reply_markup=main_keyboard)

# Обработка кнопки "Изменить продолжительность"
@dp.message(lambda message: message.text == "Изменить продолжительность")
async def change_default_duration(message: types.Message, state: FSMContext):
    await message.reply("Введите новую продолжительность в минутах:")
    await state.set_state(UserInputStates.waiting_for_duration)

# Обработка новой продолжительности
@dp.message(UserInputStates.waiting_for_duration)
async def set_new_duration(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        duration = int(message.text)
        update_default_duration(user_id, duration)
        await message.reply(f"Продолжительность по умолчанию обновлена на {duration} минут.", reply_markup=main_keyboard)
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите число.")

# Основная функция для запуска бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
