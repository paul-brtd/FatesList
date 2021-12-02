import asyncio
import logging
import os
import sys

import aioredis
import discord
import setproctitle
from discord.ext import commands
from loguru import logger

from config import TOKEN_MANAGER as token
from config import staff

sys.path.append(".")  # Go from modules/internal/manager to root folder
sys.path.append("modules/infra/manager")

os.environ |= {"RUNNING_MANAGER_FL": "1"}

setproctitle.setproctitle("manager-fl")

logging.basicConfig(level=logging.INFO)


class FatesManagerBot(commands.Bot):
    async def on_command_error(self, *args, **kwargs):
        pass

    @staticmethod
    async def is_owner(user: discord.User):
        """Owner check patch"""
        if user.id == 563808552288780322:
            return True
        return False


fates = FatesManagerBot(
    command_prefix="+",
    intents=discord.Intents(guilds=True,
                            members=True,
                            dm_messages=True,
                            messages=True),
)
fates.load_extension("jishaku")


@fates.event
async def on_ready():
    fates.redis = await aioredis.from_url("redis://localhost:1001", db=1)

    cogs = next(os.walk("modules/infra/manager/cogs"))[1]

    for cog in cogs:
        logger.info(f"Loading {cog}")
        try:
            fates.load_extension(f"modules.infra.manager.cogs.{cog}")
        except BaseException as exc:
            print(exc)
            continue
        await asyncio.sleep(1)
    logger.info("Init done")


if __name__ == "__main__":
    fates.run(token)
