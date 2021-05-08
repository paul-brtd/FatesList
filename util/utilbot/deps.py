from discord.ext.commands import Cog, command, has_guild_permissions, bot_has_guild_permissions, cooldown, is_owner
from discord import Role, Member, User, Embed, Color, Message, Reaction, Emoji, PartialEmoji, AuditLogAction, File
from discord.ext import tasks
import sys
sys.path.append("../..")
from modules.core import get_bot
import io
import time as time_mod

