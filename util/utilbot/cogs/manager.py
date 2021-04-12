from deps import *

class Manager(Cog):
    def __init__(self, client):
        self.client = client

    @command(pass_context = True)
    @has_guild_permissions(manage_roles = True)
    async def reactrole(self, ctx, message: Message, role: Role, emoji: PartialEmoji):
        reactions = await models.Reaction.filter(emoji_id = emoji.id, message_id = message.id, channel_id = message.channel.id)
        if len(reactions) != 0:
            return await ctx.send("Reaction role already exists. Use delreactrole to remove it.")
        react_role = models.Reaction(channel_id = message.channel.id, message_id = message.id, role_id = role.id, emoji_id = emoji.id)
        await react_role.save()
        await message.add_reaction(emoji)
        await ctx.send("Setup reaction for this message successfully")
    
    @command(pass_context = True)
    @has_guild_permissions(manage_roles = True)
    async def delreactrole(self, ctx, message: Message, emoji: PartialEmoji = None):
        if emoji is None:
            emoji_kw = {}
        else:
            emoji_kw = {"emoji_id": emoji.id}
        reactions = await models.Reaction.filter(**emoji_kw, message_id = message.id, channel_id = message.channel.id)
        i = 0
        for reaction in reactions:
            try:
                channel = ctx.guild.get_channel(reaction.channel_id)
                msg = await channel.fetch_message(reaction.message_id)
                await msg.clear_reaction(emoji)
            except:
                pass
            await reaction.delete()
            i+=1
        return await ctx.send(f"Removed {i} reaction roles for this message")

    @cooldown(1, 20)
    @command(pass_context = True)
    async def botdev(self, ctx):
        check = await self.client.fldb.fetchval("SELECT COUNT(1) FROM bot_owner INNER JOIN bots ON bot_owner.bot_id = bots.bot_id  WHERE bot_owner.owner = $1 AND (bots.state = 0 OR bots.state = 6)", ctx.author.id) # Get all owners
        if check == 0:
            return await ctx.send("You have no eligible bots (your bot is not verified and/or does not belong to you as a owner or extra owner)")
        await ctx.author.add_roles(ctx.guild.get_role(self.client.bot_dev_role))
        return await ctx.send("Added the role for you :)")

    @command(pass_context = True)
    async def bot(self, ctx, bot: Member):
        if bot.bot:
            await bot.add_roles(ctx.guild.get_role(self.client.bots_role))

def setup(client):
    client.add_cog(Manager(client))
