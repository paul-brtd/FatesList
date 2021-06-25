import orjson

from .core import *


def get_badges(user_dpy, blist, bots):
    states = [obj["state"] for obj in bots]
    certified = True if enums.BotState.certified in states else False 
    bot_dev = True if (enums.BotState.certified in states or enums.BotState.approved in states) else False
    if blist is None:
        blobj = []
    else:
        blobj = blist
    if user_dpy is None:
        return {}

    if isinstance(user_dpy, discord.Member):
        staff = is_staff(staff_roles, user_dpy.roles, 2)[0]
        support_server_member = True
    else:
        staff = False
        support_server_member = False
    all_badges = {}
    for badge in blobj: # Add in user created badges from blist
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
