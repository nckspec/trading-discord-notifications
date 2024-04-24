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
TRADING_BOT_URL = str(os.environ['TRADING_BOT_URL'])

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
        content = message.embeds[0].description
        LOGGER.debug("Entering get_price_from_message()\n"
                     f"content: {content}\n")

        price = re.findall(r"[-+]?(?:\d*\.*\d+)", f"{content}")
        if len(price) > 0:
            LOGGER.info(f"The price was retrieved from the message. price: {price[0]}")

            return float(price[0])

    except Exception as ex:
        message = f"Error in get_price_from_message(): {ex}"
        raise Exception(message)


#  Will check if the message came from the appropriate channel and from the bot.
def verify_price_notification(message):
    try:
        LOGGER.debug("Entering verify_price_notification()\n"
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
                    return True
        return False

    except Exception as ex:
        message = f"Error in verify_price_notification(): {ex}"
        raise Exception(message)

#  Sends a price notification to the bot's api endpoint with the specified base url
def send_price_notification(url, price):
    try:
        #  Create a new thread to send the price notification so that we can send
        #  out many price notifications quickly
        def thread(url, price):
            #  Send price to Trading Bot
            url = f'{url}/notify/?price={price}'
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


def update_user_account(discord_username, toggle, value):
    success = False
    endpoint = TRADING_BOT_URL + "/accounts/update/set"

    #  format the proper json for the /accounts/update endpoint
    data = {
        "discord_username": discord_username,
        "toggle": toggle,
        "value": value
    }

    response = requests.post(endpoint, json=data)

    if response.status_code == 200:
        success = True
    else:
        success = False

    return success, response.json()['message']


def get_help():
    #  format a response that entails all a user needs to run commands on their account
    response = f"Commands:\n" \
               f"'info' - This command will return the current settings of your account.\n\n" \
               f"'set' [Toggle] [Value] - This command will allow you to set a specific setting on your account.\n\n" \
               f"Here is a list of available settings: \n" \
               f"\n'entry_offset' - This setting will control how much lower or higher your spread will be from the" \
               f"alert notification.\n" \
               f"Example: 'set entry_offset -40' will make it so your account will trade at 40 points below the alert.\n" \
               f"\n'minimum_account_balance' - This setting will allow you to control the minimum balance your account" \
               f" must be at before it increases contracts from 1.\n" \
               f"Example: 'set minimum_account_balance 7000' will make it so your account will trade only 1 contract if" \
               f" the account balance is below $7000.\n" \
               f"\n'contract_coefficient'  -  This is the amount of money that equates to 1 contract being traded on your account." \
               f" This by default is set to $5000. This means that your account will trade 3 contracts if you have a balance of " \
               f"$15,000.\n" \
               f"Example: 'set contract_coefficient 3500' will make it so that your account will trade 10 contracts if your " \
               f"account balance is $35,000."
    return response

def get_account_info(discord_username):
    #  call the /accounts/get endpoint. Get the json and format it into a readable response
    endpoint = f"{TRADING_BOT_URL}/accounts/get/?username={discord_username}"

    response = requests.get(endpoint)

    if response.status_code == 200:

        response = response.json()

        account_info = f"**Account Info:**"
        for key in response:
            account_info = account_info + f"\n{key}: {response[key]}"

        return account_info
    elif response.status_code == 201:
        return response.json()['message']
    else:
        return None



def send_command_to_trading_bot(discord_username, command):
    response = ""
    success = False

    #  make the command lowercase and split the command by spaces
    command = command.lower().split()


    #  Check if first word is 'set'
    #  if so, check if there are three words total, then perform an update
    if command[0] == "set":
        help =  "Command: set [toggle] [value]\n" \
                       "Example: set minimum_account_balance 7000"

        if len(command) == 3:
            #  Capitalize true/false so that the endpoint can insert it directly into field
            if command[2] == "true" or command[2] == "false":
                command[2] = command[2].capitalize()

            if command[1] == "bearish_put_spread":
                command[1] = "bearish_bet"

            success, response = update_user_account(discord_username, command[1], command[2])

            #  If the command was not successful, append the help message below it
            if not success:
                response = response + f"\n{help}"

        else:
            response = help


    #  if word is help, then return a tutorial.
    elif command[0] == "help" and len(command) == 1:
        response = get_help()


    #  if word is info then return the account info
    elif command[0] == "info" and len(command) == 1:
        response = get_account_info(discord_username)

    elif command[0] == "activate" and len(command) == 1:
        success, response = update_user_account(discord_username, "activated", "True")
        if success:
            response = "The bot has been activated."

    elif command[0] == "deactivate" and len(command) == 1:
        success, response = update_user_account(discord_username, "activated", "False")
        if success:
            response = "The bot has been deactivated."

    else:
        response = f"That is not a valid command. Please type 'help' into the chat for instructions."

    return response