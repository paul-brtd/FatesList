import asyncio
import os
import sys
import io
import builtins
from typing import Optional, Union
from lynxfall.rabbit.client.core import add_rmq_task
import discord
from discord.ext.commands import Cog, command, is_owner
from config import main_server
from modules.core import get_bot

def splitc(s, l = 1990):
    o = []
    while s:
        o.append(s[:l])
        s = s[l:]
    return o

class Manager(Cog):
    def __init__(self, client, app):
        self.client = client
        self.app = app
        builtins.app = app
        builtins.discord = client
        builtins.get_bot = get_bot


    @is_owner()
    @command(pass_context = True)
    async def reload(self, ctx):
        await self.app.state.redis.publish("_worker", "RESTART IPC")
        return await ctx.send("Fates List Reload Triggered")

    @is_owner()
    @command(pass_context = True, aliases = ["bis"])
    async def botinserver(self, ctx, m: Optional[int] = 0):
        if not m:
            return await ctx.send("m of 1 means get all bots on list but not server. 2 means server but not list")

        worker_session = self.app.state.worker_session
        bot_lst = await worker_session.postgres.fetch("SELECT bot_id, state FROM bots WHERE state = 0 OR state = 6")
        bots = []
        guild = worker_session.discord.main.get_guild(main_server)
        if not guild:
            return await ctx.send("**Error** Discord is not yet up!")

        if m == 1:
            async def strategy():
                for bot in bot_lst:
                    _tmp = []
                    obj = guild.get_member(bot["bot_id"])
                    if obj:
                        continue
                    obj = await get_bot(bot["bot_id"])
                    if not obj:
                        continue
                    bots.append(f"{bot['bot_id']}\nCertified: {bot['state'] == 6}\nInvite: https://discord.com/api/oauth2/authorize?client_id={bot['bot_id']}&permission=0&scope=bot\n\n")

        if m == 2:
            async def strategy():
                ids = [obj["bot_id"] for obj in bot_lst]
                for member in guild.members:
                    if member.bot and member.id not in ids:
                        bots.append(f"{member.id}")

        await strategy()
        
        iob = io.BytesIO("\n".join(bots).encode("utf-8"))
        await ctx.send(file = discord.File(filename = f"bis-{m}.txt", fp = iob))

    @is_owner()
    @command(pass_context = True)
    async def guildcount(self, ctx, bot_id: int, count: int):
        worker_session = self.app.state.worker_session
        await worker_session.postgres.execute("UPDATE bots SET guild_count = $2 WHERE bot_id = $1", bot_id, count)
        await ctx.send("Done")
