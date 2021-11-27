from core import BotAdminOp, Status, MenuState, request, BotState, BotListView, MiniContext
from discord.ext import commands
from discord import Embed, User, Color
import discord
import asyncio
from http import HTTPStatus
from typing import Optional
from aenum import IntEnum
from copy import deepcopy
from config import testing, site_url
import dislash

class Action(IntEnum):
    approve = 0
    deny = 1
    claim = 2
    unclaim = 3

class _Handler():
    def __init__(self, bot):
        self.bot = bot

    async def queue(self, interaction):
        queue = await request("GET", interaction, "/api/queue/bots", dragon_auth=False)
        queue_json = queue[1]
        if len(queue_json["bots"]) == 0:
            return await interaction.send("There are no bots in queue right now!", ephemeral=True)
        embed = Embed(title = "Bots In Queue", description = "These are the bots in the Fates List Queue. Be sure to review them from top to bottom, ignoring Fates List bots")
        embed.set_thumbnail(url = str(interaction.guild.icon.url))
        embeds = [] # List of queue bot embeds
        i, e = 0, 0 # i is global bot counter, e is local bot counter, always between 0 and 7
        count = 1
        msgs = []
        for bot in queue_json["bots"]: # Get all bots in 5 different embeds based on base_embed
            if e == 7 or i == 0: # Check if we are locally at the next 7 sum (0, 1, 2, 3...) or if the global counter is 0 (first embed set)
                embeds.append(embed)
                embed = Embed()
                embed.set_thumbnail(url = str(interaction.guild.icon.url))
                i += 1
                e = 0
            embeds[i - 1].add_field(name = f"{count}. {bot['user']['username']}#{bot['user']['disc']} ({bot['user']['id']})", value = f"This bot has a status of **{Status(bot['user']['status']).__doc__}** and a prefix of **{bot['prefix']}** -> [Invite Bot]({site_url}/bot/{bot['user']['id']}/invite)\n\n**Description:** {bot['description']}\n​")
            e += 1
            count += 1
        
        embeds[-1].add_field(name="Credits", value="skylarr#6666 - For introducing me to redbot and hosting Fates List\nNotDraper#6666 - For helping me through a variety of bugs in the bot")
        txtc = 0
        i = 0
        msgs.append([])
        for e in embeds:
            msgs[i].append(e) 
            txtc += len(e)
            if txtc > 6000:
                i += 1
                txtc = 0
                msgs.append([])
        
        i = 0

        while i < len(msgs):
            if msgs[i]:
                await interaction.send(embeds=msgs[i], ephemeral=True)
            i+=1
  
class Testing(commands.Cog):
    def __init__(self, bot):
        self.handler = _Handler(bot)
        self.bot = bot

    @commands.slash_command(name="queue", description="Lists the Fates List bot queue", guild_ids=[testing])
    async def queue(self, inter):
        return await self.handler.queue(inter)
