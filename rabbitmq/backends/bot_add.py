from modules.core import get_bot, get_token, bot_add_event
from modules.models import enums
import discord
from config import bot_logs, staff_ping_add_role
import asyncio

async def bot_add_backend(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, invite, features, long_description_type, css, donate, github, webhook, webhook_type, vanity, privacy_policy, nsfw):
    print(bot_id)
    await db.execute("DELETE FROM bots WHERE bot_id = $1", bot_id)
    await db.execute("DELETE FROM bot_owner WHERE bot_id = $1", bot_id)
    await db.execute("DELETE FROM vanity WHERE redirect = $1", bot_id)
    await db.execute("DELETE FROM bot_tags WHERE bot_id = $1", bot_id)
    await db.execute("""INSERT INTO bots (
            bot_id, prefix, bot_library,
            invite, website, banner, 
            discord, long_description, description,
            votes, servers, shard_count,
            api_token, features, long_description_type, 
            css, donate, github, 
            webhook, webhook_type, privacy_policy, 
            nsfw) VALUES(
            $1, $2, $3,
            $4, $5, $6,
            $7, $8, $9,
            $10, $11, $12,
            $13, $14, $15,
            $16, $17, $18,
            $19, $20, $21,
            $22)""", bot_id, prefix, library, invite, website, banner, support, long_description, description, 0, 0, 0, get_token(132), features, long_description_type, css, donate, github, webhook, webhook_type, privacy_policy, nsfw) # Add new bot info
    if vanity.replace(" ", "") != '':
        await db.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", enums.Vanity.bot, vanity, bot_id) # Add new vanity if not empty string


    async with db.acquire() as connection: # Acquire a connection
        async with connection.transaction() as tr: # Use a transaction to prevent data loss
            await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot_id, user_id, True) # Add new main bot owner
            extra_owners_add = [(bot_id, owner, False) for owner in extra_owners] # Create list of extra owner tuples for executemany executemany
            await connection.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

    async with db.acquire() as connection: # Acquire a connection
        async with connection.transaction() as tr: # Use transaction to prevent data loss
            tags_add = [(bot_id, tag) for tag in tags] # Get list of bot_id, tag tuples for executemany
            await connection.executemany("INSERT INTO bot_tags (bot_id, tag) VALUES ($1, $2)", tags_add) # Add all the tags to the database

    await bot_add_event(bot_id, "add_bot", {}) # Send a add_bot event to be succint and complete 
    owner = int(user_id)
    channel = client.get_channel(bot_logs)
    bot_name = (await get_bot(bot_id))["username"]
    add_embed = discord.Embed(title="New Bot!", description=f"<@{owner}> added the bot <@{bot_id}>({bot_name}) to queue!", color=0x00ff00)
    add_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
    try:
        member = channel.guild.get_member(owner)
        if member is not None:
            await member.send(embed = add_embed) # Send user DM if possible
    except:
        pass
    await channel.send(f"<@&{staff_ping_add_role}>", embed = add_embed) # Send message with add bot ping
