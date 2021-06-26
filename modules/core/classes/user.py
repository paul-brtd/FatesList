from .base import DiscordUser
    
class User(DiscordUser):
    async def fetch(self):
        """Fetch a user object from our cache"""
        return await get_user(self.id)

    async def profile(self):
        """Gets a users profile"""
        user = await self.db.fetchrow(
            "SELECT badges, state, description, css, coins, js_allowed, vote_epoch FROM users WHERE user_id = $1", 
            self.id
        )
        
        if user is None:
            return None
        
        user_obj = await self.fetch()
        if user_obj is None:
            return None
        
        user = dict(user)
    
        # TODO: This whole section
        _bots = await self.db.fetch(
            """SELECT bots.description, bots.prefix, bots.banner, bots.state, bots.votes, bots.servers, bots.bot_id, bots.nsfw FROM bots 
            INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id 
            WHERE bot_owner.owner = $1""",
            self.id
        )
        
    bots = [dict(obj) | {"invite": await Bot(id = obj["bot_id"]).invite_url() for obj in _bots]
    approved_bots = [obj for obj in bots if obj["state"] in (enums.BotState.approved, enums.BotState.certified)]
    certified_bots = [obj for obj in bots if obj["state"] == enums.BotState.certified]
                         
    guild = self.client.get_guild(main_server)
    if guild is None:
        badges = None
                         
    else:                      
        user_dpy = guild.get_member(self.id)
        if user_dpy is None:
            user_dpy = await self.client.fetch_user(self.id)
    
    if user_dpy is None: # Still connecting to dpy or whatever
        user["badges"] = None # Still not prepared to deal with it since we havent connected to discord yet 
                         
    else:
        user["badges"] = Badge.from_user(user_dpy, badges, approved_bots)
                         
    return {
        "bots": bots, 
        "approved_bots": approved_bots, 
        "certified_bots": certified_bots, 
        "bot_developer": approved_bots != [], 
        "certified_developer": certified_bots != [], 
        "profile": user, 
        "defunct": user_dpy is None, 
        "user": user_obj
    }
