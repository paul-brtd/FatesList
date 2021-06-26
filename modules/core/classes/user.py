from .base import DiscordUser
    
class User(DiscordUser):
    """A user on Fates List"""
    async def fetch(self):
        """Fetch a user object from our cache"""
        return await get_user(self.id)

    async def profile(self):
        """Gets a users profile"""
        user = await self.db.fetchrow(
            "SELECT badges, state, description, css, js_allowed FROM users WHERE user_id = $1", 
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
        
    bots = [dict(bot) | {"invite": await Bot(id = bot["bot_id"]).invite_url() for bot in _bots]
    approved_bots = [obj for obj in bots if obj["state"] in (enums.BotState.approved, enums.BotState.certified)]
    certified_bots = [obj for obj in bots if obj["state"] == enums.BotState.certified]
    
    user["bot_dev"] = approved_bots != []
    user["cert_dev"] = certified_bots != []                      
                         
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
        user["badges"] = Badge.from_user(user_dpy, badges, user["bot_dev"], user["cert_dev"])
                         
    return {
        "bots": bots, 
        "approved_bots": approved_bots, 
        "certified_bots": certified_bots, 
        "profile": user, 
        "dup": user_dpy is None, 
        "user": user_obj
    }
