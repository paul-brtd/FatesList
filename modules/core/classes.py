# Work in progress partial rewrite of Fates List
from pydantic import BaseModel
from .cache import get_bot, get_user, get_any

class Badge():
    """Handle badges"""
    @staticmethod
    def from_user(member: discord.Member, badges: Optional[List[str]] = [], bots: list):
        """Make badges from a user given the member, badges and bots"""
        # Get core informatiom
        states = [obj["state"] for obj in bots]
        certified = True if enums.BotState.certified in states else False 
        bot_dev = True if (enums.BotState.certified in states or enums.BotState.approved in states) else False
        
        badges = badges if badges else []

        # A discord.Member is part of the support server
        if isinstance(user_dpy, discord.Member):
            staff = is_staff(staff_roles, user_dpy.roles, 2)[0]
            support_server_member = True
            
        else:
            staff = False
            support_server_member = False
        
        all_badges = {}
        for badge in badges: # Add in user created badges from blist
            try:
                badge_data = orjson.loads(badge)
            except:
                continue
                
            all_badges[badge_data["id"]] = {"name": badge_data["name"], "description": badge_data["description"], "image": badge_data["image"]}
    
    # Special staff + certified badges (if present)
    for badge_id, badge_data in special_badges.items():
        if badge_data.get("staff") and staff:
            all_badges[badge_id] = badge_data
            
        elif badge_data.get("certified") and certified:
            all_badges[badge_id] = badge_data
            
        elif badge_data.get("bot_dev") and bot_dev:
            all_badges[badge_id] = badge_data
            
        elif badge_data.get("support_server_member") and support_server_member:
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
            user_id
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
            user_id
        )
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
        badges = user["badges"] = Badge.from_user(user_dpy, badges, approved_bots)
    return {"bots": bots, "approved_bots": approved_bots, "certified_bots": certified_bots, "bot_developer": approved_bots != [], "certified_developer": certified_bots != [], "profile": user_ret, "badges": badges, "defunct": user_dpy is None, "user": user_obj}
