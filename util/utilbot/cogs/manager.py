from deps import *

class Manager(Cog):
    def __init__(self, client):
        self.client = client

    @cooldown(1, 20)
    @command(pass_context = True)
    async def botdev(self, ctx):
        check = await self.client.fldb.fetchval("SELECT COUNT(1) FROM bot_owner INNER JOIN bots ON bot_owner.bot_id = bots.bot_id  WHERE bot_owner.owner = $1 AND (bots.state = 0 OR bots.state = 6)", ctx.author.id) # Get all owners
        if check == 0:
            return await ctx.send("You have no eligible bots (your bot is not verified and/or does not belong to you as a owner or extra owner)")
        await ctx.author.add_roles(ctx.guild.get_role(self.client.bot_dev_role))
        return await ctx.send("Added the role for you :)")

    @is_owner()
    @command(pass_context = True)
    async def botinserver(self, ctx):
        bots = []
        bot_lst = await self.client.fldb.fetch("SELECT bot_id, state FROM bots WHERE state = 0 OR state = 6")
        for bot in bot_lst:
            obj = ctx.guild.get_member(bot["bot_id"])
            if obj is not None:
                continue
            obj = await get_bot(bot["bot_id"])
            if obj is None:
                continue
            bots.append(str(bot["bot_id"]) + " - " + f"\nCertified: {bot['state'] == 6}\nInvite: https://discord.com/api/oauth2/authorize?client_id={bot['bot_id']}&permission=0&scope=bot")
        iob = io.BytesIO("\n".join(bots).encode("utf-8"))
        await ctx.send(file = File(filename = "bis.txt", fp = iob))
    
    @command(pass_context = True)
    async def bot(self, ctx, bot: Member):
        if bot.bot:
            await bot.add_roles(ctx.guild.get_role(self.client.bots_role))

def setup(client):
    client.add_cog(Manager(client))
