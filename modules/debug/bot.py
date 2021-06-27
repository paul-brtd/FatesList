import asyncio
import os
import sys

import discord
from discord.ext.commands import AutoShardedBot, Bot

sys.path.append("../..")
from modules.core import *
from config import (TOKEN_MAIN, bot_dev_role, bots_role, owner, rabbitmq_pwd,
                    worker_key)

intents = discord.Intents.default()
intents.members = True
intents.typing = False
class ASB(AutoShardedBot):
    async def is_owner(self, user: discord.User):
        if user.id == owner:
            return True
        return False


# Set the roles in client
client = ASB(command_prefix = "fl!", intents = intents)

client.load_extension("jishaku")
client.bots_role = bots_role
client.bot_dev_role = bot_dev_role

def splitc(s, l = 1990):
    o = []
    while s:
        o.append(s[:l])
        s = s[l:]
    return o

class Manager(Cog):
    def __init__(self, client):
        self.client = client

    @is_owner()
    @command(pass_context = True)
    async def reload(self, ctx):
        os.system("../../bin/reload")
        return await ctx.send("Fates List Reload Triggered")

    @is_owner()
    @command(pass_context = True, aliases = ["bis"])
    async def botinserver(self, ctx):
        cmd = """
db_lst = await db.fetch("SELECT bot_id, state FROM bots WHERE state = 0 OR state = 6")
return [dict(obj) for obj in db_lst]
        """
        _ret, status = await add_rmq_task_with_ret("_admin", {}, op = cmd)
        if not status:
            return await ctx.send("**Error:** RabbitMQ is down right now.")
        if _ret["err"]:
            return await ctx.send("**Error:** An internal error has occurred")
        bot_lst = _ret["ret"]
        bots = []
        for bot in bot_lst:
            obj = ctx.guild.get_member(bot["bot_id"])
            if obj is not None:
                continue
            obj = await get_bot(bot["bot_id"])
            if obj is None:
                continue
            bots.append(str(bot["bot_id"]) + " - " + f"\nCertified: {bot['state'] == 6}\nInvite: https://discord.com/api/oauth2/authorize?client_id={bot['bot_id']}&permission=0&scope=bot")
        iob = io.BytesIO("\n".join(bots).encode("utf-8"))
        await ctx.send(file = DFile(filename = "bis.txt", fp = iob))

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

client.add_cog(Manager(client))

if __name__ == "__main__":
    client.run(TOKEN_MAIN)
