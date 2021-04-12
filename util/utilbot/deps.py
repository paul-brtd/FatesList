from discord.ext.commands import Cog, command, has_guild_permissions, bot_has_guild_permissions, cooldown
from discord import Role, Member, User, Embed, Color, Message, Reaction, Emoji, PartialEmoji, AuditLogAction
from discord.ext import tasks
import models
import time as time_mod

async def get_user_obj(id, related = None):
    if related:
        user_obj = await models.User.filter(id=id).prefetch_related(related)
    else:
        user_obj = await models.User.filter(id=id)
    if user_obj == []:
        user_obj = models.User(id = id, level = 0)
        await user_obj.save()
        return await get_user_obj(id, related)
    return user_obj[0]

modifier_dict = {
    "s": 1,
    "m": 60,
    "h": 60*60,
    "d": 60*60*24,
    "w": 60*60*24*7
}
