import asyncio
import lib
from discord import Client
client = Client()

a = lib.FatesClient(api_token = "DCUaswGL6wmGskYFlVpLbIX6RcjPvnlCkzCkTPI0WiQZoqLGLjDdETA1U6gsS6tK")

@client.event
async def on_ready():
    c = await a.set_guild_shard_count(len(client.guilds), client.shard_count)
    print(c)
client.run("Nzk4OTUxNTY2NjM0Nzc4NjQx.X_8foQ.r3oWyE87FQAXx-Kf5ueyGfzDui4")
