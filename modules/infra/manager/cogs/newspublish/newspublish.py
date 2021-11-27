import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands
from config import news_channels, message_logs_channel, staff
from loguru import logger

class NewsPublish(commands.Cog):
    """Modified version of https://github.com/SharkyTheKing/Sharky/blob/master/newspublish/core.py"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listens for news
        """

        channel, guild = message.channel, message.guild

        if not isinstance(message.guild, discord.Guild):
            return
        if channel.id not in news_channels:
            return
        try:
            await asyncio.wait_for(message.publish(), timeout=60)
            logger.info("Published message in {} - {}".format(guild.id, channel.name))
            return await self.send_alert_message(message=message, alert_type="Success")
        except asyncio.TimeoutError:
            logger.info(
                "Failed to publish message in {} - {}".format(guild.id, channel.name)
            )
            return await self.send_alert_message(message=message, alert_type="HTTPException")

    async def send_alert_message(self, message, alert_type):
        """
        Sends alert if it exists.
        Guild = message.guild
        """
        channel, guild = message.channel, message.guild

        embed = discord.Embed()

        if alert_type == "HTTPException":
            embed.title = "Failed Publish"
            embed.description = (
                "Can't publish [message in {}]({}). Hit 10 publish per user cap.".format(
                    channel.mention, message.jump_url
                )
            )

            try:
                return await self.bot.get_channel(message_logs_channel).send(embed=embed)
            except discord.Forbidden:
                logger.info(
                    "Forbidden. Couldn't send message to {} - {} channel.".format(
                        guild.id, message_logs_channel
                    )
                )

        if alert_type == "Success":
            embed.title = "Success Publish"
            embed.description = "[Published new message in {}.]({})".format(
                channel.mention, message.jump_url
            )

            try:
                return await self.bot.get_channel(message_logs_channel).send(embed=embed)
            except discord.Forbidden:
                logger.info(
                    "Forbidden. Couldn't send message to {} - {} channel.".format(
                        guild.id, message_logs_channel
                    )
                )
