import asyncio
import fates_client as lib
from discord.ext import commands
client = commands.AutoShardedBot(command_prefix = '$')

a = lib.FatesClient(api_token = "nZRaztiR7G1WqkvQzGmyhizqFsjWq8gEB7jzYwKk9tAzdOsb8F5RngYp9yUoqa0Z26iVaMtfEaWYXSRofitlzYX7jSVbF1Y1mYfs2")
print(lib.features)

def do_smth_else(v):
    print("Amount of votes: ", v.get_votes(), type(v.get_votes()))
    print("Voter: ", v.get_voter(), type(v.get_voter()))

async def my_f(v):
    print(v)
    do_smth_else(v)

@client.event
async def on_ready():
    print("Connected to discord")
    fh = lib.FatesHook(a)
    fh.start_ws_task("/tw", port = 8010, func = my_f)
    print("I am meowing not blocking")

@client.command(pass_context = True)
async def tst(ctx):
    await ctx.send("Hello mrrow")

client.run("Nzk4OTUxNTY2NjM0Nzc4NjQx.X_8foQ.r3oWyE87FQAXx-Kf5ueyGfzDui4")
