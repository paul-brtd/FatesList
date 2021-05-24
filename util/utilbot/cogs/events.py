from deps import *
from modules.core import *

class Events(Cog):
    def __init__(self, client):
        self.client = client
        self.whitelist = {}

    @command(pass_context = True)
    async def whitelist(self, ctx, bot_id: int):
        staff = is_staff(staff_roles, client.get_guild(main_server).get_member(ctx.author.id).roles, 4)
        if not staff[0]:
            return await ctx.send("You cannot temporarily whitelist this member")
        self.whitelist[bot_id] = True
        await ctx.send("Temporarily whitelisted for one minute")
        await asyncio.sleep(60)
        try:
            del self.whitelist[bot_id]
        except:
            pass
        await ctx.send("Unwhitelisted bot again")


    @Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            if member.guild.id == main_server:
                await member.add_roles(member.guild.get_role(self.client.bots_role))
            elif member.guild.id == test_server:
                await member.add_roles(member.guild.get_role(test_botsrole))
            elif not self.whitelist.get(member.id):
                await member.kick(reason = "Unauthorized Bot")
            else:
                del self.whitelist[member.id]
        else:
            staff = is_staff(staff_roles, client.get_guild(main_server).get_member(member.id).roles, 2)
            if staff[0]:
                await member.add_roles(member.guild.get_role(test_staffrole))
def setup(client):
    client.add_cog(Events(client))
