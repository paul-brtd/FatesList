import asyncio
import json
import time
import uuid
import sys
sys.path.append(".")
sys.path.append("../../../")


import ws

from modules.models import enums
bot_id = input("Enter Bot ID: ")
try:
    bot_id = int(bot_id)
except ValueError:
    bot_id = 811073947382579200

if bot_id == 811073947382579200:
    api_token = "55gCmZ7zr12upTnQcvnrXcJv1IfN15ddk9WLlxG0h54uCGKFi2TBPlOFh8RYhbCMaSDQPCju2k0g2pykEmsD3AmEvUNPoc4Rxqjk6fpNqncjk8PVeh2ImolpaXE1cNEdCVEh"
else:
    api_token = input("Enter API Token: ")

bot = ws.Bot(bot_id, api_token, True, True)
bot.start()