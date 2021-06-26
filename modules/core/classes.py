# Work in progress partial rewrite of Fates List
from pydantic import BaseModel
from .cache import get_bot, get_user, get_any

class Badge():
    """Handle badges"""
    @staticmethod
    def from_user(member: discord.Member, badges: Optional[List[str]] = [], bots: list):
        """Make badges from a user given the member, badges and bots"""
        user_flags = {}
        
        # Get core information
        states = [bot["state"] for bot in bots]
        user_flags["certified"] = enums.BotState.certified in states
        user_flags["bot_dev"] = enums.BotState.certified in states or enums.BotState.approved in states
        
        badges = badges if badges else []

        # A discord.Member is part of the support server
        if isinstance(user_dpy, discord.Member):
            user_flags["staff"] = is_staff(staff_roles, user_dpy.roles, 2)[0]
            user_flags["support_server_member"] = True
        
        all_badges = {}
        for badge in badges: # Add in user created badges from blist
            try:
                badge_data = orjson.loads(badge)
            except:
                loguru.warning("Failed to open user badge")
                continue
                
            all_badges[badge_data["id"]] = {
                "name": badge_data["name"], 
                "description": badge_data["description"], 
                "image": badge_data["image"]
            }
    
    # Special staff + certified badges (if present)
    for badge_id, badge_data in special_badges.items():
        for key in ("staff", "certified", "bot_dev", "support_server_member"):
            # Check if user is allowed to get badge and if so, give it
            if badge_data.get(key) and user_flags.get(key):
                all_badges[badge_id] = badge_data
            
        if badge_data.get("everyone"):
            all_badges[badge_id] = badge_data
            
    return all_badges

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
            self.id
        )
        
        if user is None:
            return Nome
        
        user_obj = await self.fetch()
        if user_obj is None:
            return None
        
        user = dict(user)
    
        # TODO: This whole section
        _bots = await db.fetch(
            """SELECT bots.description, bots.prefix, bots.banner, bots.state, bots.votes, bots.servers, bots.bot_id, bots.nsfw, bot_owner.main FROM bots 
            INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id 
            WHERE bot_owner.owner = $1""",
            self.id
        )
        
    bots = [dict(obj) | {"invite": await Bot(id = obj["bot_id"]).invite_url() for obj in _bots]
    approved_bots = [obj for obj in bots if obj["state"] in (enums.BotState.approved, enums.BotState.certified)]
    certified_bots = [obj for obj in bots if obj["state"] == enums.BotState.certified]
                         
    guild = client.get_guild(main_server)
    if guild is None:
        badges = None
                         
    else:                      
        user_dpy = guild.get_member(self.id)
        if user_dpy is None:
            user_dpy = await client.fetch_user(self.id)
    
    if user_dpy is None: # Still connecting to dpy or whatever
        badges = None # Still not prepared to deal with it since we havent connected to discord yet 
                         
    else:
        badges = user["badges"] = Badge.from_user(user_dpy, badges, approved_bots)
                         
    return {
        "bots": bots, 
        "approved_bots": approved_bots, 
        "certified_bots": certified_bots, 
        "bot_developer": approved_bots != [], 
        "certified_developer": certified_bots != [], 
        "profile": user, 
        "badges": badges,
        "defunct": user_dpy is None, 
        "user": user_obj
    }

class Bot(DiscordUser):
    async def fetch(self):
        """Fetch a user object from our cache"""
        return await get_user(self.id)
    
    async def invite_url(self):
        """Fetch the discord invite URL without any side effects"""
        bot = await db.fetchrow("SELECT invite, invite_amount FROM bots WHERE bot_id = $1", self.id)
        if bot is None:
            return None
        
        if not bot["invite"] or bot["invite"].startswith("P:"):
            perm = bot["invite"].split(":")[1].split("|")[0] if bot["invite"] and bot["invite"].startswith("P:") else 0
            return f"https://discord.com/api/oauth2/authorize?client_id={self.id}&permissions={perm}&scope=bot%20applications.commands"
        
        return bot["invite"]
    
    async def invite(self, user_id: Optional[int] = None):
        """Invites a user to a bot updating invite amount"""
        await db.execute("UPDATE bots SET invite_amount = invite_amount + 1 WHERE bot_id = $2", self.id)
        await add_ws_event(bot_id, {"m": {"e": enums.APIEvents.bot_invite}, "ctx": {"user": str(user_id)}})
        return await self.invite_url()
