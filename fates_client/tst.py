import asyncio
import lib
from discord import Client
client = Client()

a = lib.FatesClient(api_token = "nZRaztiR7G1WqkvQzGmyhizqFsjWq8gEB7jzYwKk9tAzdOsb8F5RngYp9yUoqa0Z26iVaMtfEaWYXSRofitlzYX7jSVbF1Y1mYfs2")
print(lib.features)

@client.event
async def on_ready():
    print("Connected to discord")
    await lib.start_ws("/tw")
    print("Done2")

@client.event
async def on_message(msg):
    print(msg)

client.run("Nzk4OTUxNTY2NjM0Nzc4NjQx.X_8foQ.r3oWyE87FQAXx-Kf5ueyGfzDui4")
