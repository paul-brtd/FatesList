from deps import *

class Events(Cog):
    def __init__(self, client):
        self.client = client

    @Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            await member.add_roles(member.guild.get_role(self.client.bots_role))

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        return await self._react_role_event(payload)
    
    @Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        return await self._react_role_event(payload)
        
    async def _react_role_event(self, payload):
        guild = self.client.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member:
            pass
        elif payload.member:
            member = payload.member
        else:
            return
        
        if member.bot:
            return
        
        print(payload.emoji.id)
        reaction = await models.Reaction.filter(emoji_id = payload.emoji.id, message_id = payload.message_id, channel_id = payload.channel_id)
        
        # Always take the zeroth element
        if len(reaction) == 0:
            return
    
        reaction = reaction[0]
        
        role = guild.get_role(reaction.role_id)
        if role:
            if payload.event_type == "REACTION_ADD":
                await member.add_roles(role)
            else:
                await member.remove_roles(role)

def setup(client):
    client.add_cog(Events(client))
