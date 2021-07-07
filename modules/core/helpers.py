"""
Helper functions for mundane tasks like getting maint, promotion or bot commands
and/or setting bot stats and voting for a bot. Also has replace tuples to be handled
"""

import re

import bleach
from lxml.html.clean import Cleaner
import asyncpg

from .auth import *
from .cache import *
from .events import *
from .imports import *
from .templating import *

# Some replace tuples
# TODO: Move this elsewhere
js_rem_tuple = (("onclick", ""), ("onhover", ""), ("script", ""), ("onload", ""))
banner_replace_tuple = (("\"", ""), ("'", ""), ("http://", "https://"), ("(", ""), (")", ""), ("file://", ""))
ldesc_replace_tuple = (("window.location", ""), ("document.ge", ""))

cleaner = Cleaner(remove_unknown_tags=False)

def worker_session(request: Request):
    return request.app.state.worker_session

async def get_maint(bot_id: str) -> Union[bool, Optional[dict]]:
    api_data = await db.fetchrow("SELECT type, reason, epoch FROM bot_maint WHERE bot_id = $1", bot_id)
    if api_data is None:
        return {"type": 0, "reason": None, "epoch": None, "fail": True}
    api_data = dict(api_data)
    api_data["epoch"] = str(time.time())
    return api_data

async def get_promotions(bot_id: int) -> list:
    api_data = await db.fetch("SELECT id, title, info, css, type FROM bot_promotions WHERE bot_id = $1", bot_id)
    return api_data

async def get_bot_commands(bot_id: int, lang: str, filter: Optional[str] = None) -> dict:
    await db.execute("DELETE FROM bot_commands WHERE cmd_groups = $1", []) # Remove unneeded commands
    if filter:
        extra = "AND name ilike $2"
        args = (f'%{filter}%',)
    else:
        extra, args = "", []
    cmd_raw = await db.fetch(f"SELECT id, cmd_groups, cmd_type, cmd_name, friendly_name, description, args, examples, premium_only, notes, doc_link FROM bot_commands WHERE bot_id = $1 {extra}", bot_id, *args)
    cmd_dict = {}
    for cmd in cmd_raw:
        for group in cmd["cmd_groups"]:
            if not cmd_dict.get(group):
                cmd_dict[group] = []
            _cmd = dict(cmd)
            for key in _cmd.keys():
                if isinstance(_cmd[key], str):
                    try:
                        _cmd[key] = cleaner.clean_html(intl_text(_cmd[key], lang)).replace("<p>", "").replace("</p>", "")
                    except Exception:
                        _cmd[key] = bleach.clean(intl_text(_cmd[key], lang)).replace("<p>", "").replace("</p>", "")
                elif isinstance(_cmd[key], list):
                    try:
                        _cmd[key] = [cleaner.clean_html(intl_text(el, lang)).replace("<p>", "").replace("</p>", "") for el in _cmd[key]]
                    except Exception:
                        _cmd[key] = [bleach.clean(intl_text(el, lang)).replace("<p>", "").replace("</p>", "") for el in _cmd[key]]

            cmd_dict[group].append(_cmd)
    return cmd_dict

async def add_maint(bot_id: int, type: int, reason: str):
    maints = await db.fetchrow("SELECT bot_id FROM bot_maint WHERE bot_id = $1", bot_id)
    if maints is None:
        return await db.execute("INSERT INTO bot_maint (bot_id, reason, type, epoch) VALUES ($1, $2, $3, $4)", bot_id, reason, type, time.time())
    await db.execute("UPDATE bot_maint SET reason = $1, type = $2, epoch = $3 WHERE bot_id = $4", reason, type, time.time(), bot_id)
    
async def set_stats(*, bot_id: int, guild_count: int, shard_count: int, user_count: int, shards: int):
    if int(guild_count) > 300000000000 or int(shard_count) > 300000000000:
        return
    await db.execute("UPDATE bots SET last_stats_post = NOW(), servers = $1, shard_count = $2, user_count = $3, shards = $4 WHERE bot_id = $5", guild_count, shard_count, user_count, shards, bot_id)

async def add_promotion(bot_id: int, title: str, info: str, css: str, type: int):
    if css is not None:
        css = css.replace("</style", "").replace("<script", "")
    info = info.replace("</style", "").replace("<script", "")
    return await db.execute("INSERT INTO bot_promotions (bot_id, title, info, css, type) VALUES ($1, $2, $3, $4, $5)", bot_id, title, info, css, type)

async def vote_bot(user_id: int, bot_id: int, autovote: bool, test: bool = False, pretend: bool = False) -> Optional[tuple]:
    epoch = await db.fetchval("SELECT vote_epoch FROM users WHERE user_id = $1", user_id)
    if not epoch or test:
        pass
    else:
        if autovote:
            WT = datetime.timedelta(hours = 11) # Autovote Wait Time
        else:
            WT = datetime.timedelta(hours = 8) # Wait Time
        if datetime.datetime.now(epoch.tzinfo) - epoch < WT: # Subtract the two times
            return epoch, WT - (datetime.datetime.now(epoch.tzinfo) - epoch)

    if not test:
        votes = await db.fetchval("SELECT votes FROM bots WHERE bot_id = $1", bot_id)
        ts = await db.fetchval("SELECT timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", bot_id, user_id)
        if votes is None:
            return None
    else:
        votes = 11
    if pretend:
        return True
    if not test:
        if ts is None:
            await db.execute("INSERT INTO bot_voters (user_id, bot_id) VALUES ($1, $2)", user_id, bot_id)
        else:
            ts.append(datetime.datetime.now())
            await db.execute("UPDATE bot_voters SET timestamps = $1 WHERE bot_id = $2 AND user_id = $3", ts, bot_id, user_id)
        await db.execute("UPDATE bots SET votes = votes + 1 WHERE bot_id = $1", bot_id)
        await db.execute("UPDATE users SET vote_epoch = NOW() WHERE user_id = $1", user_id)

        # Update bot_stats
        check = await db.fetchrow("SELECT bot_id FROM bot_stats_votes WHERE bot_id = $1", bot_id)
        if check is None:
            await db.execute("INSERT INTO bot_stats_votes (bot_id, total_votes) VALUES ($1, $2)", bot_id, votes + 1)
        else:
            await db.execute("UPDATE bot_stats_votes SET total_votes = total_votes + 1 WHERE bot_id = $1", bot_id)
        await db.execute("UPDATE user_reminders SET resolved = false, remind_time = NOW() + interval '8 hours' WHERE user_id = $1 AND bot_id = $2", user_id, bot_id)
    asyncio.create_task(bot_add_event(bot_id, enums.APIEvents.bot_vote, {"user": str(user_id), "votes": votes + 1, "test": test}))
    return True

async def invite_bot(bot_id: int, user_id = None, api = False):
    bot = await db.fetchrow("SELECT invite, invite_amount FROM bots WHERE bot_id = $1", bot_id)
    if bot is None:
        return None
    if not bot["invite"] or bot["invite"].startswith("P:"):
        perm = bot["invite"].split(":")[1].split("|")[0] if bot["invite"] and bot["invite"].startswith("P:") else 0
        return f"https://discord.com/api/oauth2/authorize?client_id={bot_id}&permissions={perm}&scope=bot%20applications.commands"
    if not api:
        await db.execute("UPDATE bots SET invite_amount = $1 WHERE bot_id = $2", bot["invite_amount"] + 1, bot_id)
    await add_ws_event(bot_id, {"m": {"e": enums.APIEvents.bot_invite}, "ctx": {"user": str(user_id), "api": api}})
    return bot["invite"]

# Check vanity of bot 
async def vanity_bot(vanity: str) -> Optional[str]:
    """Checks and returns the vanity of the bot, otherwise returns None"""

    if vanity in reserved_vanity: # Check if vanity is reserved and if so, return None
        return None

    t = await db.fetchrow("SELECT type, redirect FROM vanity WHERE lower(vanity_url) = $1", vanity.lower()) # Check vanity against database
    if t is None:
        return None # No vanity found
    
    type = enums.Vanity(t["type"]).name # Get type using Vanity enum
    return int(t["redirect"]), type

async def parse_index_query(worker_session, fetch: List[asyncpg.Record]) -> list:
    """
    Parses a index query to a list of partial bots
    """
    lst = []
    for bot in fetch:
        try:
            bot_info = await get_bot(bot["bot_id"], worker_session = worker_session)
            if bot_info is not None:
                bot = dict(bot)
                votes = bot["votes"]
                bot["bot_id"] = str(bot["bot_id"])
                servers = bot["servers"]
                del bot["votes"]
                del bot["servers"]
                banner = bot["banner"] if bot["banner"] else ""
                del bot["banner"]
                if bot_info.get("avatar") is None:
                    bot_info["avatar"] = ""
                lst.append({
                    "avatar": bot_info["avatar"].replace("?size=1024", "?size=128"),
                    "username": bot_info["username"],
                    "votes": human_format(votes), 
                    "servers": human_format(servers),
                    "description": bot["description"], 
                    "banner": banner.replace("\"", "").replace("'", "").replace("http://", "https://").replace("file://", "")
                } | bot | bot_info)
        except KeyboardInterrupt:
            return
    return lst

async def do_index_query(
    worker_session,
    add_query: str = "",
    state: list = [0, 6],
    limit: Optional[int] = 12
) -> List[asyncpg.Record]:
    """
    Performs a 'index' query which can also be used by other things as well
    """
    db = worker_session.postgres
    
    states = "WHERE " + " OR ".join([f"state = {s}" for s in state])
    base_query = f"SELECT description, banner, state, votes, servers, bot_id, invite, nsfw FROM bots {states}"
    if limit:
        end_query = f"LIMIT {limit}"
    else:
        end_query = ""
    logger.debug(base_query, add_query, end_query)
    fetch = await db.fetch(" ".join((base_query, add_query, end_query)))
    return await parse_index_query(worker_session, fetch)

async def vanity_check(id, vanity):
    """Check if a vanity exists or not given a id and a vanity"""
    if vanity.replace(" ", "") == "":
        return False
    vanity_check = await db.fetchrow("SELECT DISTINCT vanity_url FROM vanity WHERE lower(vanity_url) = $1 AND redirect != $2", vanity.replace(" ", "").lower(), id) # Get distinct vanitiss
    if vanity_check is not None or vanity.replace("", "").lower() in reserved_vanity or "/" in vanity.replace("", "").lower():
        return True
    return False
