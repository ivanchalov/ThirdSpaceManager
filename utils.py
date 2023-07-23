import os
import logging
from datetime import datetime, timedelta
import time
# from zoneinfo import ZoneInfo
from pytz import timezone as ZoneInfo

class LambdaLoggerHandler(logging.Handler):
    def emit(self, record):
        message = self.format(record)
        print(f"{record.levelname}: {message}")

def get_logger(name: str):
    # create logger
    logger = logging.getLogger(name=name)

    if "AWS_EXECUTION_ENV" in os.environ:
        logger.handlers = []  # Remove all handlers
        logger.propagate = False
        handler = LambdaLoggerHandler()
        formatter = logging.Formatter("[%(asctime)s] - %(name)s - %(message)s")
    else:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] - %(levelname)s - %(name)s - %(message)s")

    formatter.converter = time.gmtime

    # add formatter to handler
    handler.setFormatter(formatter)

    # add handler to logger
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger

def sleep_until(target_time_str, timezone_str, offset_seconds=0):
    timezone = ZoneInfo(timezone_str)
    now = datetime.now(timezone)

    target_time = datetime.strptime(target_time_str, "%H:%M").time()

    if now.time() <= target_time:
        # Only sleep if target time is in the future of this day
        # Otherwise no need to sleep
        target_datetime = now.replace(hour=target_time.hour, minute=target_time.minute, second=target_time.second, microsecond=target_time.microsecond)

        target_datetime = target_datetime + timedelta(seconds=offset_seconds)

        delay = (target_datetime - now).total_seconds()
        time.sleep(delay)

def is_class_within_window(class_time_str, timezone_str, window_minutes):
    timezone = ZoneInfo(timezone_str)
    now = datetime.now(tz=timezone)
    window_start = now + timedelta(minutes=-3)  # In case we're just past the booking time
    window_end = now + timedelta(minutes=window_minutes)
    class_time = datetime.strptime(class_time_str, "%H:%M").time()

    if window_start.time() < class_time and window_end.time() >= class_time:
        return True
    
    return False

def day_after_tomorrow(iso_weekday):
    days_of_week = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
    day_after_tomorrow = (iso_weekday + 2 - 1) % 7 + 1
    return days_of_week[day_after_tomorrow].lower()

def lowercase_and_substitute(input_str):
    lowercase_str = input_str.lower()
    replaced_str = lowercase_str.replace(" ", "-")
    return replaced_str
