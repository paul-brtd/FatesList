import discord
import asyncpg
import asyncio
from discord.ext import commands, tasks
import builtins
from config import *
from modules.core import *
from typing import Optional
import logging
logging.basicConfig(level=logging.INFO)
intent = discord.Intents.default()
intent.members = True
intent.typing = False
intent.presences = False

class ASB(commands.AutoShardedBot):
    async def is_owner(self, user: discord.User):
        if user.id == owner:
            return True
        return False

client = ASB(command_prefix='!', intents=intent)
client.load_extension("jishaku")

async def setup_db():
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    return db

@client.event
async def on_ready():
    builtins.db = await setup_db()
    print("Manager Bot Is UP")

@client.event
async def on_member_join(member):
    print(member.guild.get_role(bots_role))
    if member.bot:
        await member.add_roles(member.guild.get_role(bots_role))

#@client.command()
async def approve(ctx, bot: discord.Member):
    bot_id = bot.id
    guild = client.get_guild(main_server)
    if is_staff(staff_roles, guild.get_member(ctx.author.id).roles, 2)[0]:
        check = await db.fetchrow("SELECT owner FROM bots WHERE bot_id = $1 AND queue = true", bot_id)
        if check is None:
            return await ctx.send("This bot doesn't exist on our database or is not in the queue")
        owner = check["owner"]
        await db.execute("UPDATE bots SET queue=$2 WHERE bot_id = $1", bot_id, False)
        channel = client.get_channel(bot_logs)
        await channel.send(f"<@{bot_id}> by <@{ctx.guild.get_member(owner).id}> has been approved")
        await ctx.send("Approved this bot :)")
    else:
        await ctx.send("You don't have the permission to do this")

#@client.command()
async def deny(ctx, bot: discord.Member, *, reason: Optional[str] = "There was no reason specified"):
    guild = client.get_guild(main_server)
    bot_id = bot.id
    if is_staff(staff_roles, guild.get_member(ctx.author.id).roles, 2)[0]:
        check = await db.fetchrow("SELECT owner FROM bots WHERE bot_id = $1 AND queue = true", bot_id)
        if check is None:
            return await ctx.send("This bot doesn't exist on our database or is not in the queue")
        owner = check["owner"]
        channel = client.get_channel(bot_logs)
        await db.execute("UPDATE bots SET banned = true WHERE bot_id = $1", bot_id)
        channel = client.get_channel(bot_logs)
        await channel.send(f"<@{str(ctx.author.id)}> denied the bot <@{bot_id}> by <@{ctx.guild.get_member(owner).id}> with the reason: {reason}")
        await ctx.send("MAGA'd this bot :)")
    else:
        await ctx.send("You don't have the permission to do this")

@commands.cooldown(1, 20)
@client.command(pass_context = True)
async def botdev(ctx):
    check = await db.fetchval("SELECT COUNT(1) FROM bot_owner INNER JOIN bots ON bot_owner.bot_id = bots.bot_id  WHERE bot_owner.owner = $1 AND bots.state = 0", ctx.author.id) # Get all owners
    if check == 0:
        return await ctx.send("You have no eligible bots (your bot is not verified and/or does not belong to you as a owner or extra owner)")
    await ctx.author.add_roles(ctx.guild.get_role(bot_dev_role))
    return await ctx.send("Added the role for you :)")

@client.command(pass_context = True)
async def bot(ctx, bot: discord.Member):
    if bot.bot:
        await bot.add_roles

client.run(TOKEN_MAIN)
