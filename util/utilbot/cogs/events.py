from deps import *

class Events(Cog):
    def __init__(self, client):
        self.client = client

    @Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            await member.add_roles(member.guild.get_role(self.client.bots_role))

def setup(client):
    client.add_cog(Events(client))
