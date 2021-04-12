from deps import *

class Misc(Cog):
    def __init__(self, client):
        self.client = client
    
    @command(pass_context = True)
    async def catid(self, ctx):
        """Returns the category ID"""
        if ctx.channel.category:
            return await ctx.send(str(ctx.channel.category.id))
        return await ctx.send("No category attached to this channel")

def setup(client):
    client.add_cog(Misc(client))