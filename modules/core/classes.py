# Work in progress partial rewrite of Fates List
from pydantic import BaseModel
from .cache import get_bot, get_user, get_any

class Badge():
    pass

class DiscordUser(BaseModel):
    id: int

    # TODO: Is this the best way to do this
    async def fetch(self):
        """Generic method to fetch a user"""
        return await get_any(self.id)
      
class User(DiscordUser):
    async def fetch(self):
        """Fetch a user object from our cache"""
        return await get_user(self.id)

    async def profile(self):
        """Gets a users profile"""
        user = await db.fetchrow(
            "SELECT badges, state, description, css, coins, js_allowed, vote_epoch FROM users WHERE user_id = $1", 
            user_id
        )
        
        if user is None:
            return Nome
        
        user_obj = await self.fetch()
        if user_obj is None:
            return None
        
        user = dict(user)
        user["badges"] = Badge.from_array(user["badges"])
    
        # TODO: This whole section
        _bots = await db.fetch(
            "SELECT bots.description, bots.prefix, bots.banner, bots.state, bots.votes, bots.servers, bots.bot_id, bots.nsfw, bot_owner.main FROM bots INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id WHERE bot_owner.owner = $1", user_id)
    bots = [dict(obj) | {"invite": await invite_bot(obj["bot_id"], api = True)} for obj in _bots]
    approved_bots = [obj for obj in bots if obj["state"] in (0, 6)]
    certified_bots = [obj for obj in bots if obj["state"] == 6]
    guild = client.get_guild(main_server)
    if guild is None:
        return abort(503)
    user_dpy = guild.get_member(user_id)
    if user_dpy is None:
        user_dpy = await client.fetch_user(user_id)
    if user_dpy is None: # Still connecting to dpy or whatever
        badges = None # Still not prepared to deal with it since we havent connected to discord yet 
    else:
        badges = get_badges(user_dpy, badges, approved_bots)
    return {"bots": bots, "approved_bots": approved_bots, "certified_bots": certified_bots, "bot_developer": approved_bots != [], "certified_developer": certified_bots != [], "profile": user_ret, "badges": badges, "defunct": user_dpy is None, "user": user_obj}
