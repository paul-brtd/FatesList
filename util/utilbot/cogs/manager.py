from deps import *
from modules.core import *
import os

class Manager(Cog):
    def __init__(self, client):
        self.client = client

    @cooldown(1, 5)
    @command(pass_context = True)
    async def botdev(self, ctx):
        cmd = f"return await db.fetchval('SELECT COUNT(1) FROM bot_owner INNER JOIN bots ON bot_owner.bot_id = bots.bot_id WHERE bot_owner.owner = $1 AND (bots.state = 0 OR bots.state = 6)', {ctx.author.id})"
        status, _ret = await add_rmq_task_with_ret("_admin", {}, op = cmd)
        if not status:
            return await ctx.send("**Error:** RabbitMQ is down right now. Please make a support ticket to get the Bot Developer role")
        if _ret["err"][0]:
            return await ctx.send(f"**Error:** An internal error has occurred. Please make a support ticket to get the Bot Developer role\n\nDebug: {_ret}")
        check = _ret["ret"][0]
        if check == 0:
            return await ctx.send("You have no eligible bots (your bot is not verified and/or does not belong to you as a owner or extra owner)")
        await ctx.author.add_roles(ctx.guild.get_role(self.client.bot_dev_role))
        return await ctx.send("Added the role for you :)")

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
        status, _ret = await add_rmq_task_with_ret("_admin", {}, op = cmd)
        if not status:
            return await ctx.send("**Error:** RabbitMQ is down right now.")
        if _ret["err"][0]:
            return await ctx.send("**Error:** An internal error has occurred")
        bot_lst = _ret["ret"][0]
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
        status, _ret = await add_rmq_task_with_ret("_admin", {}, op = cmd)
        return await self.rmq_handler(ctx, status, _ret)

    @is_owner()
    @command(pass_context = True)
    async def rmqret(self, ctx, id):
        status, _ret = await rmq_get_ret(id)
        return await self.rmq_handler(ctx, status, _ret)

    async def rmq_handler(self, ctx, status, _ret):
        if not status:
            await ctx.send(f"Failed to get message from worker (likely busy). Return UUID is {_ret} and return prefix is rabbit-")
        
        err = _ret["err"]
        ret = "\n\n\n".join([f"Error: {_ret['err'][i]}\n\nReturn\n\n{_ret['ret'][i]}" for i in range(0, len(_ret["err"]))])
        await ctx.send(f"```{ret}```")

def setup(client):
    client.add_cog(Manager(client))
