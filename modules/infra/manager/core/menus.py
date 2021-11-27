import asyncio
import contextlib
import functools
from typing import Iterable, List, Union
from enum import IntEnum
import discord
from discord.ext import commands

class MenuState(IntEnum):
    rot = 0 # Running or timed out
    cancelled = 1

class MenuView(discord.ui.View):
    def __init__(self, embeds, page, timeout):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.embed = isinstance(embeds[0], discord.Embed)
        self.current = page
        self.state = MenuState.rot
    
    async def respond(self, interaction):
        if self.embed:
            await interaction.response.edit_message(embed=self.embeds[self.current])
        else:
            await interaction.response.edit_message(content='```' + self.embeds[self.current] + '```')
    
    @discord.ui.button(label='Back', emoji = '⏮️')
    async def back(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Back should go back or go to last page if going back would lead to negative index
        if self.current > 0:
            self.current -= 1
        elif len(self.embeds) > 0:
            self.current = len(self.embeds) - 1
        elif len(self.embeds) > 1:
            self.current = len(self.embeds) - 2
           
        await self.respond(interaction)
    
    @discord.ui.button(label='Cancel', emoji='❌')
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.state = MenuState.cancelled
        self.stop()
    
    @discord.ui.button(label='Next', emoji='⏭️')
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Next should go next and go to first if going next would go past the embed list
        self.current = self.current + 1 if self.current + 1 < len(self.embeds) else 0
        await self.respond(interaction)

async def menu_ctx(
    ctx: commands.Context,
    pages: Union[List[str], List[discord.Embed]],
    message: discord.Message = None,
    page: int = 0,
    timeout: float = 75.0,
):
    """
    An interaction-based menu. All pages should be of the same type (Embed or str)
    """
    if not isinstance(pages[0], (discord.Embed, str)):
        raise RuntimeError("Pages must be of type discord.Embed or str")
    if not all(isinstance(x, discord.Embed) for x in pages) and not all(
        isinstance(x, str) for x in pages
    ):
        raise RuntimeError("All pages must be of the same type")
    view = MenuView(pages, page=page, timeout=timeout)
    if message:
        await msg.edit(view=view)
    else:
        if isinstance(pages[0], discord.Embed):
            msg = await ctx.send(embed=pages[page], view=view)
        else:
            msg = await ctx.send(content='```' + pages[page] + '```', view=view)
    await view.wait()
    if view.state == MenuState.cancelled:
        s = "Cancelled"
    else:
        s = "Timed out!"
    await msg.edit(content=s, embed=None, view=None)    

