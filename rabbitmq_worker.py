"""
    RabbitMQ worker
"""
import asyncpg, asyncio, uvloop, aioredis
import sys
sys.path.append("..")
from config import *
from aio_pika import *
import discord
import orjson
import builtins
import time
from modules.core import *

intent_main = discord.Intents.default()
intent_main.typing = False
intent_main.bans = False
intent_main.emojis = False
intent_main.integrations = False
intent_main.webhooks = False
intent_main.invites = False
intent_main.voice_states = False
intent_main.messages = False
intent_main.members = True
intent_main.presences = True
client = discord.Client(intents=intent_main)

async def main():
    asyncio.create_task(client.start(TOKEN_MAIN))
    rabbitmq = await connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    builtins.db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
    # Creating a channel for edit
    channel_edit = await rabbitmq.channel()
    # Declaring queue
    queue_edit = await channel_edit.declare_queue("edit_bot_queue", durable=True)

    # Creating a channel for add
    channel_add = await rabbitmq.channel()
    # Declaring queue
    queue_add = await channel_edit.declare_queue("add_bot_queue", durable=True)

    await queue_edit.consume(edit_bot)
    await queue_add.consume(add_bot)

async def add_bot(message: IncomingMessage):
    """
    Add Bot Callback
    """
    print("Add Bot Called")
    queue = BotQueueData(orjson.loads(message.body))
    await queue.add("add_bot_queue")
    message.ack()

async def edit_bot(message: IncomingMessage):
    """
    Edit Bot Callback
    """
    print("Edit Bot called")
    queue = BotQueueData(orjson.loads(message.body))
    await queue.add("edit_bot_queue")
    message.ack()


class BotQueueData():
    def __init__(self, dict):
        if "creation" not in dict.keys():
            self.creation = time.time()
        self.__dict__.update(dict)
    
    async def add(self, queue):
        if queue == "edit_bot_queue":
            await edit_bot_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.creation, self.invite, self.webhook, self.vanity, self.github, self.features, self.html_long_description, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw) # Add edit bot to queue as background task
        elif queue == "add_bot_queue":
            await add_bot_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.creation, self.invite, self.features, self.html_long_description, self.css, self.donate, self.github, self.webhook, self.webhook_type, self.vanity, self.privacy_policy, self.nsfw) # Add bot to queue as background task

async def add_bot_backend(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, creation, invite, features, html_long_description, css, donate, github, webhook, webhook_type, vanity, privacy_policy, nsfw):
    await db.execute("""INSERT INTO bots (
            bot_id, prefix, bot_library,
            invite, website, banner, 
            discord, long_description, description,
            tags, votes, servers, shard_count,
            created_at, api_token, features, 
            html_long_description, css, donate,
            github, webhook, webhook_type, 
            privacy_policy, nsfw) VALUES(
            $1, $2, $3,
            $4, $5, $6,
            $7, $8, $9,
            $10, $11, $12,
            $13, $14, $15,
            $16, $17, $18,
            $19, $20, $21,
            $22, $23, $24)""", bot_id, prefix, library, invite, website, banner, support, long_description, description, tags, 0, 0, 0, int(creation), get_token(132), features, html_long_description, css, donate, github, webhook, webhook_type, privacy_policy, nsfw) # Add new bot info
    if vanity.replace(" ", "") != '':
        await db.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id) # Add new vanity if not empty string


    async with db.acquire() as connection: # Acquire a connection
        async with connection.transaction() as tr: # Use a transaction to prevent data loss
            await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot_id, user_id, True) # Add new main bot owner
            extra_owners_add = [(bot_id, owner, False) for owner in extra_owners] # Create list of extra owner tuples for executemany executemany
            await connection.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

    await add_event(bot_id, "add_bot", {}) # Send a add_bot event to be succint and complete 
    owner = int(user_id)
    channel = client.get_channel(bot_logs)
    while True:
        if channel is None:
            await asyncio.sleep(1)
            channel = client.get_channel(bot_logs)
        else:
            break
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


async def edit_bot_backend(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, creation, invite, webhook, vanity, github, features, html_long_description, webhook_type, css, donate, privacy_policy, nsfw):
    await db.execute("UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, tags=$9, banner=$10, invite=$11, github = $12, features = $13, html_long_description = $14, webhook_type = $15, css = $16, donate = $17, privacy_policy = $18, nsfw = $19 WHERE bot_id = $1", bot_id, library, webhook, description, long_description, prefix, website, support, tags, banner, invite, github, features, html_long_description, webhook_type, css, donate, privacy_policy, nsfw) # Update bot with new info

    async with db.acquire() as connection: # Acquire a connection
        async with connection.transaction() as tr: # Make a transaction to afoid data loss
            owners = await connection.fetch("SELECT owner FROM bot_owner where bot_id = $1 AND main = false", bot_id)
            extra_owners_ignore = [] # Extra Owners to ignore because they have already been counted in the database (already extra owners)
            extra_owners_delete = [] # Extra Owners to delete
            extra_owners_add = [] # Extra Owners to add
            for owner in owners: # Loop through owners and add to delete list if not in new extra owners
                if owner["owner"] not in extra_owners:
                    extra_owners_delete.append((bot_id, owner["owner"]))
                else:
                    extra_owners_ignore.append(owner["owner"]) # Ignore this user when adding users
            await connection.executemany("DELETE FROM bot_owner WHERE bot_id = $1 AND owner = $2 AND main = false", extra_owners_delete) # Delete in one step
            for owner in extra_owners:
                if owner not in extra_owners_ignore:
                    extra_owners_add.append((bot_id, owner, False)) # If not in ignore list, add to add list
            await connection.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

    async with db.acquire() as connection:
        async with connection.transaction():
            check = await connection.fetchrow("SELECT vanity FROM vanity WHERE redirect = $1", bot_id) # Check vanity existance
            if check is None:
                if vanity.replace(" ", "") != '': # If not there for this bot, insert new one
                    await connection.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id)
            else:
                if vanity == '':
                    vanity = None # If vanity is expty string, there is no vanity

                await connection.execute("UPDATE vanity SET vanity_url = $1 WHERE redirect = $2", vanity, bot_id) # Update the vanity since bot already use it
    await add_event(bot_id, "edit_bot", {"user": str(user_id)}) # Send event
    channel = client.get_channel(bot_logs)
    while True:
        if channel is None:
            await asyncio.sleep(1)
            channel = client.get_channel(bot_logs)
        else:
            break
    owner = int(user_id)
    edit_embed = discord.Embed(title="Bot Edit!", description=f"<@{owner}> has edited the bot <@{bot_id}>!", color=0x00ff00)
    edit_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
    await channel.send(embed = edit_embed) # Send message to channel



# Run the task
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())

    # we enter a never-ending loop that waits for data and runs
    # callbacks whenever necessary.
    print(" [*] Waiting for messages. To exit press CTRL+C")
    loop.run_forever()

