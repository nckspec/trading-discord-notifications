import discord
import os
import re
import logging
import graypy
import requests
import time

LOGGER_HOST = str(os.environ['LOGGER_HOST'])
LOGGER_PORT = int(os.environ['LOGGER_PORT'])
DISCORD_NOTIFICATIONS_CHANNEL = str(os.environ['DISCORD_NOTIFICATIONS_CHANNEL'])
DISCORD_NOTIFICATIONS_BOT = str(os.environ['DISCORD_NOTIFICATIONS_BOT'])
DISCORD_NOTIFICATIONS_DISABLE_VERIFY_BOT = bool(int(os.environ['DISCORD_NOTIFICATIONS_DISABLE_VERIFY_BOT']))
DISCORD_TOKEN = str(os.environ['DISCORD_TOKEN'])

LOGGER = logging.getLogger('discord-logger')
LOGGER.setLevel(logging.DEBUG)

handler = graypy.GELFTCPHandler(LOGGER_HOST, LOGGER_PORT)
LOGGER.addHandler(handler)


FORMAT = '%(asctime)s - %(levelname)s - %(message)s\n'
logging.basicConfig(format=FORMAT, datefmt='%m/%d/%Y %H:%M:%S')
# logging.disable(logging.DEBUG)


class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        channel = self.get_channel(1196232297893089310)
        await channel.send(embed=discord.Embed(title="test", description="NDX - $17320.3938"))





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