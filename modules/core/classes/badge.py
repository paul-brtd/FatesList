from typing import List, Optional
from modules.core.permissions import is_staff
from modules.core.logger import logger
import modules.models.enums as enums
from discord import Member
import orjson
from config import special_badges as _sbs
from pydantic import BaseModel

special_badges = [_sbs[id] | {"id": id} for id in sbs.keys()] # Until we rewrite config for badges

class Badge(BaseModel):
    """Handle badges"""
    id: str
    name: str
    description: str
    image: str
    staff: Optional[bool] = False
    certified: Optional[bool] = False
    bot_dev: Optional[bool] = False
    support_server_member: Optional[bool] = False
    everyone: Optional[bool] = False
    
    
    @staticmethod
    def from_user(member: Member, badges: Optional[List[str]] = [], bot_dev: Optional[bool] = False, cert_dev: Optional[bool] = False):
        """Make badges from a user given the member, badges and bots"""
        user_flags = {}
        
        user_flags["certified"] = cert_dev
        user_flags["bot_dev"] = bot_dev
        
        badges = badges if badges else []

        # A discord.Member is part of the support server
        if isinstance(user_dpy, discord.Member):
            user_flags["staff"] = is_staff(staff_roles, user_dpy.roles, 2)[0]
            user_flags["support_server_member"] = True
        
        all_badges = []
        for badge in badges: # Add in user created badges from blist
            try:
                badge_data = orjson.loads(badge)
            except:
                logger.warning("Failed to open user badge")
                continue
                
            all_badges.append(badge_data)
    
    # Special staff + certified badges (if present)
    for badge_id, badge_data in special_badges.items():
        for key in ("staff", "certified", "bot_dev", "support_server_member"):
            # Check if user is allowed to get badge and if so, give it
            if badge_data.get(key) and user_flags.get(key):
                all_badges.append(badge_data)
            
        if badge_data.get("everyone"):
            all_badges.append(badge_data)
            
    return all_badges
