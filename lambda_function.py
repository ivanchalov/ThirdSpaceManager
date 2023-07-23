import json
import os
import sys
import time
from datetime import datetime

import requests
import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import read_config
from utils import day_after_tomorrow, get_logger, is_class_within_window, sleep_until, lowercase_and_substitute


logger = get_logger(__name__)


THIRD_SPACE_LOGIN = os.environ.get("THIRD_SPACE_LOGIN")
THIRD_SPACE_PASSWORD = os.environ.get("THIRD_SPACE_PASSWORD")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_PAGE_ID = os.environ.get("NOTION_PAGE_ID")

THIRD_SPACE_LOGIN_URL = "https://www.thirdspace.london/login/"
THIRD_SPACE_TIMETABLE_URL = "https://www.thirdspace.london/timetable/"

NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": "Bearer " + NOTION_API_KEY,
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION}

BOOKING_WINDOW_MINUTES = 15
MAX_RETRIES = 3


def initialise_chrome_driver(config):

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")

    if "AWS_EXECUTION_ENV" in os.environ:
        options.binary_location = config.get("chrome_binary_path_aws")
        chromedriver_path = config.get("chromedriver_path_aws")
    else:
        chromedriver_path = config.get("chromedriver_path_local")

    driver = webdriver.Chrome(chromedriver_path, options=options)

    return driver

def build_date_tile_xpath(column_number):
    xpath = (f"//div[@class='fkl-cal owl-carousel owl-loaded owl-drag fkl-location-filtered']"
             f"//div[@class='owl-stage-outer']"
             f"//div[@class='owl-stage']"
             f"//div[@class='owl-item active'][{column_number}]"
             f"//div[@class='fkl-cal-col']"
             f"//div[@class='fkl-cal-th']"
             f"//div[@class='fkl-date-title']")
    return xpath

def build_class_tile_xpath(class_to_book, column_number):
    xpath = (f"//div[@class='fkl-cal owl-carousel owl-loaded owl-drag fkl-location-filtered']"
             f"//div[@class='owl-stage-outer']"
             f"//div[@class='owl-stage']"
             f"//div[@class='owl-item active'][{column_number}]"
             f"//div[@class='fkl-cal-col']"
             f"//div[contains(@class, 'fkl-cal-td') and contains(@class, 'fkl-class')]"
             f"[div[@class='fkl-class-title' and contains(text(), '{class_to_book['name']}')]]"
             f"[div[@class='fkl-time' and starts-with(text(), '{class_to_book['time']}')]]"
             f"[div[@class='fkl-sublocation' and text()='{class_to_book['location']}']]")
    return xpath

def get_correct_column_number(driver, booking_day):
    for i in range(1, 8):
        logger.info(f"Checking all date tiles, currently at: {i}")
        xpath = build_date_tile_xpath(i)
        date_tile = driver.find_element("xpath", xpath)
        tile_day = date_tile.text
        logger.info(f"{tile_day}")
        if tile_day.lower() == booking_day:
            logger.info(f"Bingo! The right column number is: {i}")
            return i

def login_to_third_space(driver, login_url, login, password):

    logger.info(f"Opening login page: {login_url}")
    driver.get(login_url)
    time.sleep(20)   # Allow the page to load, along with promo pop up window

    try:
        logger.info("Accepting cookies")
        accept_cookies_button = driver.find_element("id", "onetrust-accept-btn-handler")
        accept_cookies_button.click()
        time.sleep(1)
    except Exception as e:
        logger.warning("Failed to click accept cookies button. Maybe they were already accepted")
        logger.warning(e)

    try:
        logger.info("Closing referral promotion window")
        promo_close_button = driver.find_element("class name", "leadinModal-close")
        promo_close_button.click()
        time.sleep(1)
    except Exception as e:
        logger.warning("Failed to close promotional pop up window. Maybe the promo has ended")
        logger.warning(e)

    logger.info("Filling in details and entering")
    login_element = driver.find_element("name", "email")
    password_element = driver.find_element("name", "password")
    login_element.clear()
    password_element.clear()
    login_element.send_keys(login)
    password_element.send_keys(password)
    password_element.send_keys(Keys.RETURN)
    time.sleep(5)   # Allow the page to load

def select_club(driver, location):

    club_selector_button_css_selector = "a.fkl-change-club"
    club_button_css_selector = f"li.{lowercase_and_substitute(location)} > a"

    logger.info("Opening club selector")
    club_selector_button = driver.find_element("css selector", club_selector_button_css_selector)
    club_selector_button.click()
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located(("css selector", club_button_css_selector)))

    logger.info(f"Clicking the {location} club")
    club_button = driver.find_element("css selector", club_button_css_selector)
    club_button.click()

def proceed_with_booking(driver):

    class_booked = False

    # Specifying selectors
    book_button_css_selector = ".fkl_book_buttons input.fkl-join"
    book_confirmation_xpath = "//div[contains(@class, 'fkl-modal-inner')]//h3[text()=\"You're all set!\"] | //div[contains(@class, 'fkl-modal-inner')]//h3[text()=\"Something went wrong\"]"

    try:
        logger.info("Clicking the book button")
        book_button = driver.find_element("css selector", book_button_css_selector)
        book_button.click()

        logger.info("Waiting for the confirmation screen")
        book_confirmation_element = WebDriverWait(driver, 5)\
            .until(EC.visibility_of_element_located(("xpath", book_confirmation_xpath)))

        confirmation_outcome = book_confirmation_element.get_attribute("textContent")
        
        if confirmation_outcome == "You're all set!":
            logger.info("'You're all set!' received. Class booked")
            class_booked = True
        elif confirmation_outcome == "Something went wrong":
            logger.info(f"'Something went wrong' received. Need to retry")
            class_booked = False
        else:
            logger.error(f"Unknown confirmation received. Need to retry")
            class_booked = False

    except Exception as e:
        logger.error(f"Did not receive confirmation screen for booking. Need to retry")
        logger.error(e)

    return class_booked

def handle_booking_modal(driver, class_tile_xpath):

    class_booked = False

    # Specifying selectors
    book_modal_xpath = "//div[contains(@class, 'fkl-modal-inner')]/div[@class='fkl_book_buttons']//input[@type='submit'] | //div[contains(@class, 'fkl-modal-inner')]/div[@class='fkl_book_buttons']//p[@class='cannot_book']"
    close_button_css_selector = ".fkl-modal-inner .fkl-close"

    try:
        logger.info("Clicking the class tile")
        class_tile_element = driver.find_element("xpath", class_tile_xpath)
        class_tile_element.click()

        book_modal_element = WebDriverWait(driver, 10)\
            .until(EC.visibility_of_element_located(("xpath", book_modal_xpath)))

        class_name = book_modal_element.get_attribute("class")
        if class_name == "fkl-join":
            logger.info('Modal with "Book" button opened')

            logger.info("Proceeding to book the class")
            class_booked = proceed_with_booking(driver)
            
        elif class_name == "fkl-wait":
            logger.info('Modal with "Join Waiting List" button opened')

            logger.info("Not going to join the waiting list. Skipping the class booking")
            class_booked = True

        elif class_name == "fkl-cancel":
            logger.info('Modal with "Cancel" button opened')

            logger.info("Class already booked")
            class_booked = True

        elif class_name == "cannot_book":
            logger.info('Modal with "This class is not available to book until 48hrs before it starts" button opened')

            logger.info("Too early to book the class. Need to retry")
            class_booked = False

        else:
            logger.warning("Unknown modal opened. Skipping")
            class_booked = False

        logger.info("Clicking the close button")
        close_button = driver.find_element("css selector", close_button_css_selector)
        close_button.click()
        time.sleep(2)  # Allow the page to load

    except Exception as e:
        logger.error("No known pop-up window opened. Skipping")
        logger.error(e)

    return class_booked

def book_class(driver, timetable_url, class_to_book, booking_day):

    class_booked = False
    retries = 0

    logger.info(f"Moving to timetable page: {timetable_url}")
    driver.get(timetable_url)
    time.sleep(20)  # Allow the page to load

    logger.info("Looking up the right column to book the class")
    column_number = get_correct_column_number(driver, booking_day)
    class_tile_xpath = build_class_tile_xpath(class_to_book, column_number)

    logger.info(f"Selecting the club: {class_to_book['location']}")
    select_club(driver, class_to_book["location"])
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located(("xpath", class_tile_xpath)))
    time.sleep(10)   # Somehow above line is not enough sometimes

    logger.info(f"Sleeping until {class_to_book['time']} plus 1 second")
    sleep_until(class_to_book["time"], "Europe/London", 1)

    while not class_booked and retries < MAX_RETRIES:

        logger.info(f"Trying to book. Try {retries} of {MAX_RETRIES}")
        class_booked = handle_booking_modal(driver, class_tile_xpath)

        if not class_booked:
            time.sleep(retries ** 2 * 150)  # Retry fast first, then slower
        retries += 1

def fetch_classes():

    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"

    logger.info("Fetching schedule block from Notion")
    result = requests.get(url, headers=HEADERS)

    data = json.loads(result.text)
    content = data["results"][0]["code"]["rich_text"][0]["text"]["content"]

    classes = yaml.safe_load(content)
    logger.info(f"Classes fetched: {classes}")

    return classes

def lambda_handler(event, context):

    config = read_config("config.yaml")

    logger.info("Fetching classes from Notion")
    classes = fetch_classes()

    booking_day = day_after_tomorrow(datetime.now().isoweekday())
    logger.info(f"Booking classes for: {booking_day}")

    classes_to_book = classes[booking_day]
    logger.info(f"Classes to book: {classes_to_book}")

    if not classes_to_book:
        logger.info("No classes to book. Terminating")
        sys.exit()

    logger.info("Booking classes")
    for class_to_book in classes_to_book:

        class_is_within_booking_window = is_class_within_window(
            class_to_book["time"], "Europe/London", BOOKING_WINDOW_MINUTES)
        logger.info(f"Class {class_to_book} is within booking window of "
                    f"{BOOKING_WINDOW_MINUTES} minutes: {class_is_within_booking_window}")
        
        if not class_is_within_booking_window:
            logger.info("Outside of window, skipping")
            continue

        logger.info("Initialising Chrome Driver")
        driver = initialise_chrome_driver(config)

        logger.info("Logging into account")
        login_to_third_space(driver, THIRD_SPACE_LOGIN_URL, THIRD_SPACE_LOGIN, THIRD_SPACE_PASSWORD)

        logger.info(f"Booking class: {class_to_book}")
        book_class(driver, THIRD_SPACE_TIMETABLE_URL, class_to_book, booking_day)

        logger.info("Closing Chrome Driver")
        driver.quit()

    logger.info("Job done")

    return {
        "statusCode": 200,
        "body": json.dumps("Job done")
    }

if __name__ == "__main__":
    event, context = {}, {}
    lambda_handler(event, context)
