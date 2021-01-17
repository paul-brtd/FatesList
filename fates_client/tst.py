import asyncio
import lib
from discord import Client
a = lib.FatesClient(api_token = "", client = Client())
c = asyncio.run(a.set_guild_shard_count())
print(c)
