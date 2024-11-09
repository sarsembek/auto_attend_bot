import time
import sys
import os
import requests
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WAIT_TIME = 10
UPDATE_INTERVAL = 60
SHOW_UI = False

# Функция для отправки уведомления через Telegram
def send_notification(chat_id, bot_token, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")

# Функция попытки отметиться
def try_to_attend(selenium_driver, chat_id, bot_token):
    wait = WebDriverWait(selenium_driver, WAIT_TIME)
    page_source = selenium_driver.page_source

    if 'Нет доступных дисциплин' in page_source:
        return

    try:
        button_divs = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[span/span[@class='v-button-caption' and text()='Отметиться']]")
            )
        )

        for button_div in button_divs:
            if button_div is not None:
                button_div.click()
                time.sleep(1)
                # Уведомляем пользователя об успешной отметке
                send_notification(chat_id, bot_token, "Отметка прошла успешно!")
    except TimeoutException:
        send_notification(chat_id, bot_token, "Время ожидания истекло, не удалось отметиться.")
        return
    except Exception as e:
        print(f"Error: {e}")
        try_to_attend(selenium_driver, chat_id, bot_token)

# Основная функция
def main(username, password, duration, chat_id, bot_token):
    options = webdriver.ChromeOptions()
    if not SHOW_UI:
        options.add_argument('--headless')

    driver = webdriver.Chrome(options=options)
    driver.get("https://wsp.kbtu.kz/RegistrationOnline")

    try:
        login(driver, username, password)
        end_time = time.time() + duration * 60

        while time.time() < end_time:
            try_to_attend(driver, chat_id, bot_token)
            time.sleep(UPDATE_INTERVAL)
            driver.refresh()
    except Exception as e:
        send_notification(chat_id, bot_token, f"Ошибка в основном цикле: {e}")
        print(f"Error in main loop: {e}")
    finally:
        driver.quit()
        send_notification(chat_id, bot_token, "Скрипт завершил выполнение.")

# Функция для логина
def login(selenium_driver, username, password):
    wait = WebDriverWait(selenium_driver, WAIT_TIME)

    username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
    username_input.clear()
    username_input.send_keys(username)

    password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
    password_input.send_keys(password)

    checkbox = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="checkbox"]')))
    selenium_driver.execute_script("arguments[0].parentElement.click();", checkbox)

    submit_button = wait.until(EC.presence_of_element_located(
        (By.XPATH, '//div[@role="button" and contains(@class, "v-button-primary")]')))
    submit_button.click()

# Запуск скрипта
if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python auto_attend.py <username> <password> <duration_in_minutes> <chat_id> <bot_token>")
        sys.exit(1)

    USERNAME = sys.argv[1]
    PASSWORD = sys.argv[2]
    DURATION = int(sys.argv[3])
    CHAT_ID = sys.argv[4]
    BOT_TOKEN = sys.argv[5]
    main(USERNAME, PASSWORD, DURATION, CHAT_ID, BOT_TOKEN)
