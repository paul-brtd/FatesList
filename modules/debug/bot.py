import asyncio
import os
import sys
import io
from typing import Optional, Union
from lynxfall.rabbit.client.core import add_rmq_task_with_ret
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

    @is_owner()
    @command(pass_context = True)
    async def reload(self, ctx):
        os.system("bin/reload")
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
    async def rmq(self, ctx, *, cmd: str):
        cmd = cmd.replace("```", "").lstrip()
        _ret = await add_rmq_task_with_ret("_admin", {}, op = cmd)
        return await self.rmq_handler(ctx, _ret)

    @is_owner()
    @command(pass_context = True)
    async def rmqret(self, ctx, id):
        _ret = await rmq_get_ret(id)
        return await self.rmq_handler(ctx, _ret)

    async def rmq_handler(self, ctx, _ret):
        if not _ret[1]:
            await ctx.send(f"Failed to get message from worker (likely busy). Return UUID is {_ret[0]} and return prefix is rabbit-")
        ret = f"Error: {_ret[0]['err']}\n\nReturn\n\n{_ret[0]['ret']}"
        retl = splitc(ret)
        for r in retl:
            await ctx.send(f"```{r}```")

