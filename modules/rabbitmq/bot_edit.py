from modules.core import *
from lynxfall.rabbit.core import *


class Config:
    queue = "bot_edit_queue"
    name = "Bot Edit"
    description = "Edits a bot on Fates List"

async def backend(state, json, *, user_id, bot_id, prefix, library, website, banner_card, banner_page, support, long_description, description, tags, extra_owners, invite, webhook, vanity, github, features, long_description_type, webhook_type, webhook_secret, css, donate, privacy_policy, nsfw, **kwargs):
    await state.postgres.execute("UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, banner_card=$9, invite=$10, github = $11, features = $12, long_description_type = $13, webhook_type = $14, css = $15, donate = $16, privacy_policy = $17, nsfw = $18, webhook_secret = $19, banner_page = $20 WHERE bot_id = $1", bot_id, library, webhook, description, long_description, prefix, website, support, banner_card, invite, github, features, long_description_type, webhook_type, css, donate, privacy_policy, nsfw, webhook_secret, banner_page) # Update bot with new info

    async with state.postgres.acquire() as connection: # Acquire a connection
        async with connection.transaction() as tr: # Make a transaction to avoid data loss
            await connection.execute("DELETE FROM bot_owner WHERE bot_id = $1 AND main = false", bot_id) # Delete all extra owners
            done = []
            for owner in extra_owners:
                if owner in done:
                    continue
                await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot_id, owner, False)
                done.append(owner)

    async with state.postgres.acquire() as connection: # Acquire a connection
        async with connection.transaction() as tr: # Make a transaction to avoid data loss
            await connection.execute("DELETE FROM bot_tags WHERE bot_id = $1", bot_id) # Delete all bot tags
            done = []
            for tag in tags:
                if tag in done:
                    continue
                await connection.execute("INSERT INTO bot_tags (bot_id, tag) VALUES ($1, $2)", bot_id, tag) # Insert new bot tags
                done.append(tag)

    async with state.postgres.acquire() as connection:
        async with connection.transaction():
            check = await connection.fetchrow("SELECT vanity FROM vanity WHERE redirect = $1", bot_id) # Check vanity existance
            if check is None:
                if vanity.replace(" ", "") != '': # If not there for this bot, insert new one
                    await connection.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id)
            else:
                if vanity == '':
                    vanity = None # If vanity is expty string, there is no vanity

                await connection.execute("UPDATE vanity SET vanity_url = $1 WHERE redirect = $2", vanity, bot_id) # Update the vanity since bot already use it
    await bot_add_event(bot_id, enums.APIEvents.bot_edit, {"user": str(user_id)}) # Send event
    channel = state.client.get_channel(bot_logs)
    owner = int(user_id)
    edit_embed = discord.Embed(title="Bot Edit!", description=f"<@{owner}> has edited the bot <@{bot_id}>!", color=0x00ff00)
    edit_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
    await channel.send(embed = edit_embed) # Send message to channel
