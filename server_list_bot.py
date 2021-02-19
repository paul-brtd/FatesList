import discord
import asyncpg
import asyncio
from discord.ext import commands, tasks
import builtins
from config import *
from modules.deps import *
from typing import Optional
from fastapi import FastAPI

intent = discord.Intents.default()
client = commands.Bot(command_prefix='fl-', intents=intent)
client.remove_command("help")
app = FastAPI(default_response_class = ORJSONResponse, docs_url = None, redoc_url = "/api/docs")
server_data = {} # This is the global server data we have
setup_servers = {}
async def setup_db():
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    return db

@app.on_event("startup")
async def startup():
    builtins.db = await setup_db()
    print("Discord")
    asyncio.create_task(client.start(TOKEN_SERVER))

@client.event
async def on_ready():
    print("ServerList Bot Is UP")


async def server_data_use_check(ctx):
    await ctx.send("Oh hey, it looks like we have some prior information about your server that you have previously entered before during setup. Would you like me to use that prior data. Type 'Yes' to use it, 'No' to not use it and 'View' to view this data")
    try:
        msg = await client.wait_for('message', check = lambda m : m.author.id == ctx.author.id and m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.content.lower().replace(' ', '') in ["yes", 'no', 'view'], timeout=120)
    except:
        setup_servers[str(ctx.guild.id)] = False
        await ctx.send("Sorry, but setup has been cancelled as you have taken too long to respond (we wait 2 minutes). Please rerun this command again to readd your server")
        return None

    if msg.content == 'yes':
        return True

    elif msg.content == 'no':
        await ctx.send("Should I remove this prior information about your server? Type 'Yes' to delete it or 'No' to keep it.")
        msg = await client.wait_for('message', check = lambda m : m.author.id == ctx.author.id and m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.content.lower().replace(' ', '') in ["yes", 'no'], timeout=120)
        if msg.content == "yes":
            try:
                del server_data[str(ctx.guild.id)]
            except:
                pass
        return False

    else:
        await ctx.send("Here the json will be...")
        await ctx.send("Type 'back' to go back to the main question and proceed onwards\nType 'cancel' to exit")
        msg = await client.wait_for('message', check = lambda m : m.author.id == ctx.author.id and m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.content.lower().replace(' ', '') in ["back", 'cancel'], timeout=120)
        if msg.content.lower().replace(' ', '') == 'back':
            return await server_data_use_check(ctx)
        return None

async def prompt_user(ctx, mini, prompt, *, minlength = None, maxlength = None):
    await ctx.send(prompt + "\n*This can be changed at any time by editting your server on Fates List*\n\nType cancel to stop the prompt")
    try:
        msg = await client.wait_for('message', check = lambda m : m.author.id == ctx.author.id and m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id, timeout=120)
    except asyncio.TimeoutError:
        setup_servers[str(ctx.guild.id)] = False
        await ctx.send("Sorry, but setup has been cancelled as you have taken too long to respond (we wait 2 minutes). Please rerun this command again to readd your server")
        return None
    if msg.content == "cancel":
        setup_servers[str(ctx.guild.id)] = False
        return None
    if minlength is not None and len(msg.content) < minlength:
        await ctx.send(f"Your {mini} must be at least {minlength} characters long.\nError Code: ROOTSPRING3")
        await asyncio.sleep(1)
        return await prompt_user(ctx, mini, prompt, minlength = minlength, maxlength = maxlength)
    elif maxlength is not None and len(msg.content) > maxlength:
        await ctx.send(f"Your {mini} must be at most {maxlength} characters long\nError Code: ROOTSPRING4")
        await asyncio.sleep(1)
        return await prompt_user(ctx, mini, prompt, minlength = minlength, maxlength = maxlength)
    prompt_answer = msg.content
    await ctx.send(f"You have inputted the below for {mini}, is this correct?\n\n{msg.content}\n\nType 'yes' to continue or 'no' to redo this question")
    try:
        msg = await client.wait_for('message', check = lambda m : m.author.id == ctx.author.id and m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.content.lower().replace(' ', '') in ["yes", 'no'], timeout=120)
    except asyncio.TimeoutError:
        setup_servers[str(ctx.guild.id)] = False
        await ctx.send("Sorry, but setup has been cancelled as you have taken too long to respond (we wait 2 minutes). Please rerun this command again to readd your server")
        return None
    print("Got here")
    if msg.content.lower().replace(' ', '') == "no":
        return await prompt_user(ctx, mini, prompt, minlength = minlength, maxlength = maxlength)
    return prompt_answer

@client.command(pass_context = True)
async def setup(ctx, channel: Optional[discord.TextChannel] = None):
    use_prior_data = False # Initially

    if channel is None:
        return await ctx.send("**Error**\n\nYou must provide the channel that you want users to join into. If you want to use a user provided invite, run ``fl-setupuser <invite code>``.\n\nError Code: ROOTSPRING1")
    check = await db.fetchrow("SELECT guild_id FROM servers WHERE guild_id = $1", ctx.guild.id)
    if check is not None:
        return await ctx.send(f"**Error**\n\nThis server already exists on Fates List.\nPlease see https://{site}/servers/{ctx.guild.id} to view it on Fates List\n\nError Code: BRISTLEFROST1")
    elif setup_servers.get(str(ctx.guild.id)) == True:
        return await ctx.send(f"**Error**\n\nThis server is already being setup somewhere else on this server.\n\nError Code: BRISTLEFROST2")
    setup_servers[str(ctx.guild.id)] = True
    if server_data.get(str(ctx.guild.id)) is not None:
        rc = await server_data_use_check(ctx)
        if rc is None:
            return await ctx.send("Error Code: SHADOWSIGHT")
        use_prior_data = (rc == True)
    description = await prompt_user(ctx, "short description", "Please enter the short description for your server.", minlength = 10, maxlength = 105)
    setup_servers[str(ctx.guild.id)] = False
    return await ctx.send(description)

#CREATE TABLE servers (
#    guild_id bigint not null unique,
#    votes bigint,
#    webhook_type text DEFAULT 'VOTE',
#    webhook text,
#    description text,
#    long_description text,
#    html_long_description boolean default false,
#    css text default '',
#    api_token text unique,
#    website text,
#    tags text[],
#    certified boolean DEFAULT false,
#    created_at bigint,
#    banned BOOLEAN DEFAULT false,
#    invite_amount integer DEFAULT 0
#)


@client.command(pass_context = True)
async def setupuser(ctx, invite: Optional[str] = None):
    if invite is None:
        return await ctx.send("**Error**\n\nYou must provide the invite code you want to use. If you want Fates List to create an invite for you, run ``fl-setup <channel>``.\n\nError Code: ROOTSPRING2")

@client.command(pass_context = True)
async def help(ctx):
    return await ctx.send("**Fates List Server Listing Help**\n\nfl-setup <channel> - Sets up Fates List with automatic invite generation\nfl-setupuser <invite code> - Sets up Fates List with a user provided invite code")
