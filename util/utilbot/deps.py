import sys

from discord import AuditLogAction, Color, Embed, Emoji
from discord import File as DFile
from discord import Member, Message, PartialEmoji, Reaction, Role, User
from discord.ext import tasks
from discord.ext.commands import (Cog, bot_has_guild_permissions, command,
                                  cooldown, has_guild_permissions, is_owner)

sys.path.append("../..")
import io
import time as time_mod

from modules.core import get_bot
