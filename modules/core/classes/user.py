from .base import DiscordUser
from modules.core.cache import get_user
    
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
            """SELECT bots.description, bots.prefix, bots.banner, bots.state, bots.votes, 
            bots.servers AS guild_count, bots.bot_id, bots.nsfw FROM bots 
            INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id 
            WHERE bot_owner.owner = $1""",
            self.id
        )
        
        bots = []
        for bot in _bots:
            bot_obj = Bot(id = bot["bot_id"])
            bots.append(bot | {"invite": await bot_obj.invite_url(), "user": await bot_obj.fetch()})
        
        approved_bots = [obj for obj in bots if obj["state"] in (enums.BotState.approved, enums.BotState.certified)]
        certified_bots = [obj for obj in bots if obj["state"] == enums.BotState.certified]
    
        user["bot_dev"] = approved_bots != []
        user["cert_dev"] = certified_bots != []                      
                         
        guild = self.client.get_guild(main_server)
        if guild is None:
            user["badges"] = None
                         
        else:                      
            user_dpy = guild.get_member(self.id)            
            user["badges"] = Badge.from_user(user_dpy, badges, user["bot_dev"], user["cert_dev"])
                         
        return {
            "bots": bots, 
            "approved_bots": approved_bots, 
            "certified_bots": certified_bots, 
            "profile": user,
            "dup": Fakse
            "user": user_obj
        }
