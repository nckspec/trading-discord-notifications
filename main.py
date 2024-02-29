import discord
import os
import re
import logging
import graypy
import requests
import time
import threading

LOGGER_HOST = str(os.environ['LOGGER_HOST'])
LOGGER_PORT = int(os.environ['LOGGER_PORT'])
DISCORD_NOTIFICATIONS_CHANNEL = str(os.environ['DISCORD_NOTIFICATIONS_CHANNEL'])
DISCORD_NOTIFICATIONS_BOT = str(os.environ['DISCORD_NOTIFICATIONS_BOT'])
DISCORD_NOTIFICATIONS_DISABLE_VERIFY_BOT = bool(int(os.environ['DISCORD_NOTIFICATIONS_DISABLE_VERIFY_BOT']))
DISCORD_TOKEN = str(os.environ['DISCORD_TOKEN'])

TRADING_BOT_API_URLS = str(os.environ['TRADING_BOT_API_URLS']).split(",")

LOGGER = logging.getLogger('discord-logger')
LOGGER.setLevel(logging.DEBUG)

handler = graypy.GELFTCPHandler(LOGGER_HOST, LOGGER_PORT)
LOGGER.addHandler(handler)


FORMAT = '%(asctime)s - %(levelname)s - %(message)s\n'
logging.basicConfig(format=FORMAT, datefmt='%m/%d/%Y %H:%M:%S')
# logging.disable(logging.DEBUG)

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

class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        try:

            LOGGER.debug(f"Entering on_message()\n"
                        f"content: {message.content}\n"
                        f"discord_embed: {str(message.embeds[0].description) if len(message.embeds) else None}\n"
                        f"author: {message.author}\n"
                        f"channel: {message.channel}")

            #  Check if the message is a notification from the bot
            message = verify_message(message)
            if message:
                LOGGER.info(f"A price notification was received from the bot.")
                price = get_price_from_message(message)

                #  Send a price notification to each trading bot that is setup
                for url in TRADING_BOT_API_URLS:
                    try:
                        send_price_notification(url, price)
                    except Exception as ex:
                        LOGGER.error(f"Unable to send price notification to trading bot!\n"
                                     f"trading bot api url: {url}\n"
                                     f"Exception: {ex}")

                LOGGER.info(f"Successfully sent price to the trading bots!")
        except Exception as ex:
            message = f"Error in MyClient.on_message(): {ex}"
            raise Exception(message)


def main():
    try:

        intents = discord.Intents.default()
        intents.message_content = True

        client = MyClient(intents=intents)
        client.run(DISCORD_TOKEN)

    except Exception as ex:
        LOGGER.error(f"Error in main(): {ex}")
        time.sleep(60)
        main()


main()