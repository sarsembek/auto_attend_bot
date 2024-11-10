import time
import sys
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from db import get_user_credentials
from bot import send_notification  # Import the function from bot.py

# Configuration Constants
WAIT_TIME = 20  # Increased wait time
UPDATE_INTERVAL = 60
SHOW_UI = True

# Function to attempt attendance
def try_to_attend(driver, chat_id, bot_token):
    wait = WebDriverWait(driver, WAIT_TIME)
    page_source = driver.page_source

    if 'Нет доступных дисциплин' in page_source:
        print("No available courses found.")
        return

    try:
        # Wait for the attendance button to appear
        button_divs = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//div[span/span[@class='v-button-caption' and text()='Отметиться']]")
            )
        )

        # Click on each button to attempt attendance
        for button_div in button_divs:
            if button_div:
                button_div.click()
                time.sleep(1)
                send_notification(chat_id, "Attendance successful!")
    except TimeoutException:
        send_notification(chat_id, "Timeout reached, could not mark attendance.")
        print("Timeout reached, could not mark attendance.")
    except Exception as e:
        print(f"Error during attendance attempt: {e}")
        send_notification(chat_id, f"Error during attendance attempt: {e}")

# Function to login to the website
def login(selenium_driver, username, password):
    wait = WebDriverWait(selenium_driver, WAIT_TIME)

    username_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]')))
    if username_input is not None:
        username_input.clear()
        username_input.send_keys(username)

    time.sleep(1)

    password_input = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]')))
    if password_input is not None:
        password_input.send_keys(password)

    checkbox = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//input[@type="checkbox"]')
        )
    )
    parent_element = selenium_driver.execute_script("return arguments[0].parentElement;", checkbox)
    if parent_element is not None:
        parent_element.click()

    submit_button = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '//div[@role="button" and contains(@class, "v-button-primary")]')
        )
    )
    if submit_button is not None:
        submit_button.click()

# Main function to control the bot
def main(username, password, duration, chat_id, bot_token):
    options = webdriver.ChromeOptions()
    if not SHOW_UI:
        options.add_argument('--headless')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Use WebDriverManager to get the latest version of chromedriver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    try:
        # Open the target website
        driver.get("https://wsp.kbtu.kz/RegistrationOnline")
        login(driver, username, password)

        # Set the end time based on the duration
        end_time = time.time() + duration * 60

        # Main loop to attempt attendance every `UPDATE_INTERVAL` seconds
        while time.time() < end_time:
            try_to_attend(driver, chat_id, bot_token)
            time.sleep(UPDATE_INTERVAL)
            driver.refresh()

    except Exception as e:
        send_notification(chat_id, f"An error occurred in the main loop: {e}")
        print(f"Error in main loop: {e}")
    finally:
        driver.quit()
        send_notification(chat_id, "Script execution finished.")

# Entry point of the script
if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python auto_attend.py <username> <password> <duration_in_minutes> <chat_id> <bot_token>")
        sys.exit(1)

    USERNAME = sys.argv[1]
    PASSWORD = sys.argv[2]
    DURATION = int(sys.argv[3])
    CHAT_ID = sys.argv[4]
    BOT_TOKEN = sys.argv[5]

    # Check if the user exists in the database
    if not get_user_credentials(CHAT_ID):
        print("User does not exist in the database.")
        send_notification(CHAT_ID, "User does not exist in the database.")
        sys.exit(1)

    main(USERNAME, PASSWORD, DURATION, CHAT_ID, BOT_TOKEN)
