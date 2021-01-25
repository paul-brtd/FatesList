import asyncio
import fates_client as lib
from discord.ext import commands
client = commands.AutoShardedBot(command_prefix = '$')

a = lib.FatesClient(api_token = "TEST_WEBHOOK_ONLY")
print(lib.features)

def do_smth_else(v):
    print("Amount of votes: ", v.get_votes(), type(v.get_votes()))
    print("Voter: ", v.get_voter(), type(v.get_voter()))

async def my_f(v):
    print(v)
    do_smth_else(v)
fh = lib.FatesHook(a)
asyncio.run(fh.start_ws("/tw", port = 8010, func = my_f))
