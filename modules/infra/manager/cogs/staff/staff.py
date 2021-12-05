import asyncio
import enum
from http import HTTPStatus
from typing import Optional, Union

import discord
from core import BotAdminOp, MiniContext, UserState, is_staff, log
from discord import Color, Embed, Member, TextChannel, User
from discord.ext import commands
from loguru import logger

from config import (
    ag_role,
    log_channel,
    main,
    main_bots_role,
    staff,
    staff_roles,
    test_bots_role,
    test_staff_role,
    testing,
)

# For now
disnake = discord
dislash = commands

class Method(enum.Enum):
    GET = "GET"


class Staff(commands.Cog):
    """Commands to handle the staff server"""

    def __init__(self, bot):
        self.bot = bot
        self.whitelist = {}  # Staff Server Bot Protection

    @commands.slash_command(
        description="Bans a user from the list/Sets user state",
        guild_ids=[staff])
    async def userstate(self, inter, user: disnake.User, state: UserState,
                        reason: str):
        staff = await is_staff(inter, inter.author.id, 5)
        if not staff[0]:
            return await inter.send("You are not a Head Admin+!")
        await self.bot.postgres.execute(
            "UPDATE users SET state = $1 WHERE user_id = $2", state.value,
            user.id)
        return await inter.send(f"Set state of {user} successfully to {state}")

    @commands.slash_command(
        name="getaccess",
        description="Get access to the staff server",
        guild_ids=[staff],
    )
    async def getaccess(self, inter):
        staff = await is_staff(inter, inter.author.id, 2)
        if not staff[0]:
            try:
                msg = "You are not a Fates List Staff Member. You will hence be kicked from the staff server!"
                await inter.send(msg)
                await asyncio.sleep(3)
                await inter.author.kick()
            except:
                await inter.send(
                    "I've failed to kick this member. Staff, please kick this member now!"
                )
            return
        await inter.author.add_roles(
            inter.guild.get_role(ag_role),
            inter.guild.get_role(int(staff[2].staff_id)))
        return await inter.send("Welcome home, master!")

    @commands.slash_command(
        name="dapireq",
        description="Make a request to the discord API",
        guild_ids=[staff],
    )
    async def dapireq(self, inter, method: Method, route: str):
        route = discord.http.Route(
            method=method.value,
            path=route.replace("https://discord.com/api/",
                               "").replace("v8/", "/",
                                           1).replace("v9/", "/", 1),
        )
        try:
            res = await self.bot.http.request(route)
        except Exception as exc:
            return await inter.send(str(exc))
        return await inter.send(str(res))

    @commands.slash_command(name="botop",
                            description="Bot Admin Operations",
                            guild_ids=[staff])
    async def botop(self, inter):
        ...

    @botop.sub_command(
        name="get",
        description="Get operation",
    )
    async def get(
        self,
        inter,
    ):
        return await inter.send(
            "Please see https://docs.fateslist.xyz/structures/enums.autogen/#botadminop for the list of bot admin operations"
        )

    @dislash.slash_command(
        name="allowbot",
        description="Allows a bot temporarily to the staff server",
        guild_ids=[staff],
    )
    async def allowbot(self, inter, bot: disnake.User):
        """Shhhhh.... secret command to allow adding a bot to the staff server"""
        staff = await is_staff(inter, inter.author.id, 4)
        if not staff[0]:
            return await inter.send(
                "You cannot temporarily whitelist this member as you are not an admin"
            )
        self.whitelist[bot.id] = True
        await inter.send("Temporarily whitelisted for one minute")
        await asyncio.sleep(60)
        try:
            del self.whitelist[bot.id]
        except:
            pass
        try:
            await inter.send("Unwhitelisted bot again")
        except Exception:
            pass

    @dislash.slash_command(
        name="addstaff",
        description="Add a staff member to the team.",
        guild_ids=[staff],
    )
    async def addstaff(self, inter, user: disnake.User):
        staff_check = await is_staff(inter, inter.author.id, 5)
        if not staff_check[0]:
            return await inter.send("Only staff can use this command")

        main_guild = self.bot.get_guild(main)
        msg = f"""
**You have been accepted onto our staff team!**

In order to begin testing bots and be a part of the Fates List Staff Team, you must join the below servers:
 
 
**Staff server:** <https://fateslist.xyz/server/{staff}/invite>

**Testing server:** <https://fateslist.xyz/server/{testing}/invite>


After joining the staff server, you must run /getaccess to get your roles.
 
 
Finally, type /queue on our testing server to start testing bots. Feel free to ask any staff for help if you need it!
        """
        main_member = main_guild.get_member(user.id)
        if not main_member:
            return await inter.send("Could not find member on main server!")

        try:
            await user.send(msg)
        except Exception:
            return await inter.send(
                "Could not send DM to user. Ask them to temporarily allow DMs in order to add them as staff"
            )

        await main_member.add_roles(
            main_guild.get_role(int(staff_roles["community_staff"]["id"])),
            main_guild.get_role(int(staff_roles["bot_reviewer"]["id"])),
        )
        return await inter.send("Successfully added staff")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Anti log spam
        if not message.guild:
            return
        if (message.author.id != message.guild.me.id
                and int(message.channel.id) == log_channel):
            await message.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            if member.guild.id == main:
                await member.add_roles(member.guild.get_role(main_bots_role))
                await log(
                    MiniContext(member, self.bot),
                    f"Bot **{member.name}#{member.discriminator}** has joined the main server, hopefully after being properly tested...",
                )
            elif member.guild.id == testing:
                await member.add_roles(member.guild.get_role(test_bots_role))
                await log(
                    MiniContext(member, self.bot),
                    f"Bot **{member.name}#{member.discriminator}** has joined the testing server, good luck...",
                )
            elif not self.whitelist.get(member.id) and member.guild.id == staff:
                await member.kick(reason="Unauthorized Bot")
            else:
                del self.whitelist[member.id]
        else:
            if member.guild.id == testing:
                staff_check = await is_staff(MiniContext(member, self.bot), member.id, 2)
                if staff_check[0]:
                    await member.add_roles(
                        member.guild.get_role(test_staff_role))
