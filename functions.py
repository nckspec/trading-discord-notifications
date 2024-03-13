import logging
import re
import requests
import threading
import redis
import os
import datetime
import pytz

LOGGER = logging.getLogger('discord-logger')

DISCORD_NOTIFICATIONS_CHANNEL = str(os.environ['DISCORD_NOTIFICATIONS_CHANNEL'])
DISCORD_NOTIFICATIONS_BOT = str(os.environ['DISCORD_NOTIFICATIONS_BOT'])
DISCORD_NOTIFICATIONS_DISABLE_VERIFY_BOT = bool(int(os.environ['DISCORD_NOTIFICATIONS_DISABLE_VERIFY_BOT']))


#  Will convert the date to ooc format. Must input a date() object and
#  will return a string in ooc format
def convert_date_to_ooc(date: datetime.date):
    try:
        date_format = "%y%m%d"
        date = date.strftime(date_format)

        return date
    except Exception as ex:
        message = f"Error in functions.convert_date_to_ooc(): {ex}"
        raise Exception(message)

def get_current_date():
    date = pytz.utc.localize(datetime.datetime.utcnow())
    date = date.astimezone(pytz.timezone("America/Los_Angeles"))
    return date

#  Checks the redis server to see if the current date exists as a key
def was_price_notification_received(redis: redis.Redis):
    try:
        #  Get the date as a string in yymmdd format
        date = convert_date_to_ooc(get_current_date())

        #  Check the redis server for a key that matches the date
        price = redis.get(date)

        if price:
            return True
        else:
            return False

    except Exception as ex:
        message = f"Error in functions.was_price_notification_received(): {ex}"
        raise Exception(message)

def mark_price_notification_received(redis: redis.Redis, price):
    try:
        #  Get the date as a string in yymmdd format
        date = convert_date_to_ooc(get_current_date())

        #  Mark the price notification as the value under a key matching
        #  the current date
        redis.set(date, price)

    except Exception as ex:
        message = f"Error in functions.mark_price_notification_received(): {ex}"
        raise Exception(message)

#  Extracts the price from the Discord message as a float
def get_price_from_message(message):
    try:
        LOGGER.debug("Entering get_price_from_message()\n"
                     f"discord_message: {message}\n")

        price = re.findall(r"[-+]?(?:\d*\.*\d+)", f"{message}")
        if len(price) > 0:
            LOGGER.info(f"The price was retrieved from the message. price: {price[0]}")

            return float(price[0])

    except Exception as ex:
        message = f"Error in get_price_from_message(): {ex}"
        raise Exception(message)


#  Will check if the message came from the appropriate channel and from the bot.
#  If it
def verify_message(message):
    try:
        LOGGER.debug("Entering verify_message()\n"
                           f"discord_message: {str(message.content)}\n"
                           f"discord_embed: {str(message.embeds[0].description) if len(message.embeds) else None}\n"
                           f"discord_author: {str(message.author)}\n"
                           f"discord_channel: {str(message.channel)}")

        channel = str(message.channel)
        author = str(message.author)

        #  Check if the message came from the notifications channel
        if channel == DISCORD_NOTIFICATIONS_CHANNEL and (
                author == DISCORD_NOTIFICATIONS_BOT or DISCORD_NOTIFICATIONS_DISABLE_VERIFY_BOT is True):

            #  Check if the bot is giving a valid trade notification. The bot
            #  uses 'embeds' to put the price notification into the chat.
            if len(message.embeds) > 0:
                content = message.embeds[0].description
                if "NDX" in content:
                    return content
        return None

    except Exception as ex:
        message = f"Error in verify_message(): {ex}"
        raise Exception(message)

#  Sends a price notification to the bot's api endpoint with the specified base url
def send_price_notification(url, price):
    try:
        #  Create a new thread to send the price notification so that we can send
        #  out many price notifications quickly
        def thread(url, price):
            #  Send price to Trading Bot
            url = f'{url}/notify?price={price}'
            response = requests.post(url)

            if response.status_code == 200:
                LOGGER.info(f"Successfully sent price to trading bot!\n"
                            f"trading bot api url: {url}")
            else:
                raise Exception(f"Could not send price to the trading bot!\n"
                                f"trading bot api url: {url}")

        x = threading.Thread(target=thread, args=(url, price))
        x.start()
    except Exception as ex:
        message = f"Error in send_price_notification(): {ex}"
        raise Exception(message)