from deps import *
from modules.core import *
import os

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
        await ctx.send(f"```{ret}```")

def setup(client):
    client.add_cog(Manager(client))
