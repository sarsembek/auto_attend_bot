import os
import subprocess
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from db import init_db, save_user_credentials, get_user_credentials, update_default_duration, get_all_users, delete_user, update_user_credentials, save_user_request, get_all_requests, approve_user_request

# Load environment variables from .env file
load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID'))
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Initialize the database
init_db()

# Store Selenium processes
selenium_processes = {}

# Create buttons
buttons = [
    KeyboardButton(text="Запустить"),  # Button to start the default script
    KeyboardButton(text="Изменить продолжительность"),
    KeyboardButton(text="Просмотр пользователей"),
    KeyboardButton(text="Удалить пользователя"),
    KeyboardButton(text="Обновить пользователя"),
    KeyboardButton(text="Просмотр запросов"),
    KeyboardButton(text="Добавить пользователя")
]
main_keyboard = ReplyKeyboardMarkup(keyboard=[[button] for button in buttons], resize_keyboard=True)

# Cancel button
cancel_button = KeyboardButton(text="Отмена")
cancel_keyboard = ReplyKeyboardMarkup(keyboard=[[cancel_button]], resize_keyboard=True)

# States for Finite State Machine (FSM)
class UserInputStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_duration = State()
    waiting_for_user_id_to_delete = State()
    waiting_for_user_id_to_update = State()
    waiting_for_new_username = State()
    waiting_for_new_password = State()
    waiting_for_request_username = State()
    waiting_for_request_password = State()
    waiting_for_add_username = State()
    waiting_for_add_password = State()

# Function to send notifications via Telegram
def send_notification(chat_id, message):
    url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification: {e}")

# Command /start
@dp.message(Command(commands=["start"]))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id == ADMIN_USER_ID:
        await message.reply("Welcome, Admin! Use the buttons below to manage users.", reply_markup=main_keyboard)
    elif get_user_credentials(user_id):
        await message.reply("Welcome back! Use the buttons below to manage your attendance.", reply_markup=main_keyboard)
    else:
        await message.reply("Welcome! Please send your username to request access.")
        await state.set_state(UserInputStates.waiting_for_request_username)

# Handle request username input
@dp.message(UserInputStates.waiting_for_request_username)
async def get_request_username(message: types.Message, state: FSMContext):
    username = message.text
    await state.update_data(username=username)
    await message.reply("Please send your password.")
    await state.set_state(UserInputStates.waiting_for_request_password)

# Handle request password input
@dp.message(UserInputStates.waiting_for_request_password)
async def get_request_password(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    password = message.text
    user_data = await state.get_data()
    username = user_data.get("username")

    # Save the user request to the database
    save_user_request(user_id, username, password)

    # Notify the admin
    send_notification(ADMIN_USER_ID, f"New access request from user ID {user_id} with username {username}.")

    await message.reply("Your request has been sent to the admin for approval.")
    await state.clear()

# Command /run to start the default script
@dp.message(Command(commands=["run"]))
async def run_default_script(message: types.Message):
    await launch_script(message)

# Handle "Запустить" button
@dp.message(lambda message: message.text == "Запустить")
async def handle_run_button(message: types.Message):
    await launch_script(message)

# Function to launch the script
async def launch_script(message: types.Message):
    user_id = message.from_user.id
    if user_credentials := get_user_credentials(user_id):
        username, password, default_duration = user_credentials
        await message.reply(f"Запускаем авто отметку с продолжительностью {default_duration} минут. Ждите...", reply_markup=cancel_keyboard)
        try:
            # Start the Selenium process
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

# Handle "Отмена" button
@dp.message(lambda message: message.text == "Отмена")
async def handle_cancel_button(message: types.Message):
    user_id = message.from_user.id
    if user_id in selenium_processes:
        process = selenium_processes[user_id]
        process.terminate()
        process.wait()  # Wait for the process to terminate
        del selenium_processes[user_id]
        await message.reply("Процесс отметки был успешно остановлен.", reply_markup=main_keyboard)
    else:
        await message.reply("Нет активного процесса для остановки.", reply_markup=main_keyboard)

# Handle "Изменить продолжительность" button
@dp.message(lambda message: message.text == "Изменить продолжительность")
async def change_default_duration(message: types.Message, state: FSMContext):
    await message.reply("Введите новую продолжительность в минутах:")
    await state.set_state(UserInputStates.waiting_for_duration)

# Handle new duration input
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

# Handle "Просмотр пользователей" button
@dp.message(lambda message: message.text == "Просмотр пользователей")
async def view_users(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    users = get_all_users()
    if not users:
        await message.reply("Нет пользователей в базе данных.")
        return
    for i in range(0, len(users), 10):
        user_page = users[i:i + 10]
        user_info = "\n".join([f"ID: {user[0]}, Username: {user[1]}, Duration: {user[3]}" for user in user_page])
        await message.reply(user_info)

# Handle "Удалить пользователя" button
@dp.message(lambda message: message.text == "Удалить пользователя")
async def delete_user_prompt(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    await message.reply("Введите ID пользователя для удаления:")
    await state.set_state(UserInputStates.waiting_for_user_id_to_delete)

# Handle user ID input for deletion
@dp.message(UserInputStates.waiting_for_user_id_to_delete)
async def delete_user_by_id(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    try:
        user_id = int(message.text)
        delete_user(user_id)
        await message.reply(f"Пользователь с ID {user_id} был удален.", reply_markup=main_keyboard)
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите действительный ID пользователя.")

# Handle "Обновить пользователя" button
@dp.message(lambda message: message.text == "Обновить пользователя")
async def update_user_prompt(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    await message.reply("Введите ID пользователя для обновления:")
    await state.set_state(UserInputStates.waiting_for_user_id_to_update)

# Handle user ID input for update
@dp.message(UserInputStates.waiting_for_user_id_to_update)
async def get_user_id_for_update(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    try:
        user_id = int(message.text)
        await state.update_data(user_id=user_id)
        await message.reply("Введите новое имя пользователя:")
        await state.set_state(UserInputStates.waiting_for_new_username)
    except ValueError:
        await message.reply("Пожалуйста, введите действительный ID пользователя.")

# Handle new username input
@dp.message(UserInputStates.waiting_for_new_username)
async def get_new_username(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    new_username = message.text
    await state.update_data(new_username=new_username)
    await message.reply("Введите новый пароль:")
    await state.set_state(UserInputStates.waiting_for_new_password)

# Handle new password input
@dp.message(UserInputStates.waiting_for_new_password)
async def get_new_password(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    new_password = message.text
    user_data = await state.get_data()
    user_id = user_data.get("user_id")
    new_username = user_data.get("new_username")

    # Update user credentials in the database
    update_user_credentials(user_id, new_username, new_password)

    await message.reply(f"Данные пользователя с ID {user_id} были обновлены.", reply_markup=main_keyboard)
    await state.clear()

# Handle "Добавить пользователя" button
@dp.message(lambda message: message.text == "Добавить пользователя")
async def add_user_prompt(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    await message.reply("Введите имя пользователя для добавления:")
    await state.set_state(UserInputStates.waiting_for_add_username)

# Handle new username input for adding user
@dp.message(UserInputStates.waiting_for_add_username)
async def get_add_username(message: types.Message, state: FSMContext):
    new_username = message.text
    await state.update_data(new_username=new_username)
    await message.reply("Введите пароль для добавления пользователя:")
    await state.set_state(UserInputStates.waiting_for_add_password)

# Handle new password input for adding user
@dp.message(UserInputStates.waiting_for_add_password)
async def get_add_password(message: types.Message, state: FSMContext):
    new_password = message.text
    user_data = await state.get_data()
    new_username = user_data.get("new_username")

    # Save new user credentials to the database
    save_user_credentials(message.from_user.id, new_username, new_password)

    await message.reply(f"Пользователь {new_username} был добавлен.", reply_markup=main_keyboard)
    await state.clear()

# Handle "Просмотр запросов" button
@dp.message(lambda message: message.text == "Просмотр запросов")
async def view_requests(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("You are not authorized to use this command.")
        return
    requests = get_all_requests()
    if not requests:
        await message.reply("Нет запросов в базе данных.")
        return
    for req in requests:
        request_info = f"Request ID: {req[0]}, User ID: {req[1]}, Username: {req[2]}, Status: {req[4]}"
        approve_button = InlineKeyboardButton(text="Approve", callback_data=f"approve_{req[0]}")
        reject_button = InlineKeyboardButton(text="Reject", callback_data=f"reject_{req[0]}")
        inline_kb = InlineKeyboardMarkup().add(approve_button, reject_button)
        await message.reply(request_info, reply_markup=inline_kb)

# Handle inline button callbacks
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('approve_'))
async def approve_request(callback_query: types.CallbackQuery):
    request_id = int(callback_query.data.split('_')[1])
    approve_user_request(request_id)
    await bot.answer_callback_query(callback_query.id, text=f"Request ID {request_id} has been approved.")
    await bot.send_message(callback_query.from_user.id, f"Request ID {request_id} has been approved.")

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('reject_'))
async def reject_request(callback_query: types.CallbackQuery):
    request_id = int(callback_query.data.split('_')[1])
    # Implement the logic to reject the request if needed
    await bot.answer_callback_query(callback_query.id, text=f"Request ID {request_id} has been rejected.")
    await bot.send_message(callback_query.from_user.id, f"Request ID {request_id} has been rejected.")

# Main function to start the bot
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
