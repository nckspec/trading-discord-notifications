import discord
import os
import logging
import graypy
import time
import redis
from urllib.parse import urlparse
import functions

LOGGER_HOST = str(os.environ['LOGGER_HOST'])
LOGGER_PORT = int(os.environ['LOGGER_PORT'])

DISCORD_TOKEN = str(os.environ['DISCORD_TOKEN'])

TRADING_BOT_API_URLS = str(os.environ['TRADING_BOT_API_URLS']).split(",")

REDIS_URL = str(os.environ.get("REDIS_URL"))

LOGGER = logging.getLogger('discord-logger')
LOGGER.setLevel(logging.DEBUG)

handler = graypy.GELFTCPHandler(LOGGER_HOST, LOGGER_PORT)
LOGGER.addHandler(handler)


FORMAT = '%(asctime)s - %(levelname)s - %(message)s\n'
logging.basicConfig(format=FORMAT, datefmt='%m/%d/%Y %H:%M:%S')
# logging.disable(logging.DEBUG)

try:
    #  PROC: Define our global connection to our REDIS server
    REDIS = redis.from_url(REDIS_URL)
    REDIS.ping()

except Exception as ex:

    try:
        url = urlparse(REDIS_URL)
        REDIS = redis.Redis(host=url.hostname, port=url.port, username=url.username, password=url.password, ssl=True,
                        ssl_cert_reqs=None)
        REDIS.ping()

    except Exception as ex:
        message = f"Error when connecting to redis server: {ex}"
        LOGGER.error(message)
        raise message


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
            message = functions.verify_message(message)
            if message:
                LOGGER.info(f"A price notification was received from the NDX bot.")
                price = functions.get_price_from_message(message)

                #  Check the redis server to see if a price notification was already
                #  received on the current date
                if not functions.was_price_notification_received(REDIS):

                    #  Mark that the price notification was received in the redis server
                    functions.mark_price_notification_received(REDIS, price)

                    #  Send a price notification to each trading bot that is setup
                    for url in TRADING_BOT_API_URLS:
                        try:
                            functions.send_price_notification(url, price)
                        except Exception as ex:
                            LOGGER.error(f"Unable to send price notification to trading bot!\n"
                                         f"trading bot api url: {url}\n"
                                         f"Exception: {ex}")
                    LOGGER.info(f"Successfully sent price to the trading bots!")
                else:
                    LOGGER.warning(f"A price notification was already received today. "
                                   f"The price notification will not be relayed to the trading bots.")
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

