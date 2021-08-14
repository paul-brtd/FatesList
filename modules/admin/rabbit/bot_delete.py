from modules.core import *
from lynxfall.rabbit.core import *


class Config:
    queue = "bot_delete_queue"
    name = "Bot Delete"
    description = "Bot Delete"

async def backend(state, json, *, user_id, bot_id, **kwargs):
    await state.postgres.execute(f"DELETE FROM bots WHERE bot_id = $1", bot_id)
    await state.postgres.execute("DELETE FROM vanity WHERE redirect = $1", bot_id)

    # Check all packs
    packs = await state.postgres.fetch("SELECT bots FROM bot_packs")
    pack_bot_delete = [] # Packs to delete the bot from
    for pack in packs:
        if bot_id in pack["bots"]:
            pack_bot_delete.append((pack["id"], [id for id in pack["bots"] if id in pack["bots"]])) # Get all bots not in pack, then delete them all uaing executemany
    await state.postgres.executemany("UPDATE bot_packs SET bots = $2 WHERE id = $1", pack_bot_delete)

    delete_embed = discord.Embed(title="Bot Deleted :(", description=f"<@{user_id}> has deleted the bot <@{bot_id}>!", color=discord.Color.red())
    await bot_add_event(bot_id, "delete_bot", {"user": user_id})    
    channel = state.client.get_channel(bot_logs)
    await channel.send(embed = delete_embed)
