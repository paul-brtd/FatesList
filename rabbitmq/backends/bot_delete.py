from modules.core import bot_add_event
from config import bot_logs
import discord

async def bot_delete_backend(user_id, bot_id):
    await db.execute(f"DELETE FROM bots WHERE bot_id = $1", bot_id)
    await db.execute("DELETE FROM vanity WHERE redirect = $1", bot_id)

    # Check all packs
    packs = await db.fetch("SELECT bots FROM bot_packs")
    pack_bot_delete = [] # Packs to delete the bot from
    for pack in packs:
        if bot_id in pack["bots"]:
            pack_bot_delete.append((pack["id"], [id for id in pack["bots"] if id in pack["bots"]])) # Get all bots not in pack, then delete them all uaing executemany
    await db.executemany("UPDATE bot_packs SET bots = $2 WHERE id = $1", pack_bot_delete)

    delete_embed = discord.Embed(title="Bot Deleted :(", description=f"<@{user_id}> has deleted the bot <@{bot_id}>!", color=discord.Color.red())
    await bot_add_event(bot_id, "delete_bot", {"user": user_id})    
    channel = client.get_channel(bot_logs)
    await channel.send(embed = delete_embed)
