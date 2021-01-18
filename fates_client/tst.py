import asyncio
import fates_client as lib
from discord import Client
client = Client()

a = lib.FatesClient(api_token = "nZRaztiR7G1WqkvQzGmyhizqFsjWq8gEB7jzYwKk9tAzdOsb8F5RngYp9yUoqa0Z26iVaMtfEaWYXSRofitlzYX7jSVbF1Y1mYfs2")
print(lib.features)

def my_f(e):
    print(e)

@client.event
async def on_ready():
    print("Connected to discord")
    fh = lib.FatesHook(a)
    await fh.start_ws("/tw", port = 8010, func = my_f) # THIS IS BLOCKING BLOCKING BLOCKING
    print("Done2")

@client.event
async def on_message(msg):
    print(msg)

client.run("Nzk4OTUxNTY2NjM0Nzc4NjQx.X_8foQ.r3oWyE87FQAXx-Kf5ueyGfzDui4")
