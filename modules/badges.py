import orjson
from .core import *

def get_badges(user_dpy, blist, certified):
    print(certified, blist, user_dpy)
    if blist is None:
        blobj = []
    else:
        blobj = blist
    if user_dpy is None:
        return {}
    if type(user_dpy) == discord.User:
        roles = []
    else:
        roles = user_dpy.roles
    all_badges = {}
    for badge in blobj: # Add in user created badges from blist
        try:
            badge_data = orjson.loads(badge)
        except:
            continue
        all_badges[badge_data["id"]] = {"name": badge_data["name"], "description": badge_data["description"], "image": badge_data["image"]}
    # Special staff + certified badges (if present)
    staff = is_staff(staff_roles, roles, 2)
    for badge_id, badge_data in special_badges.items():
        if badge_data["staff"]:
            if staff[0]:
                all_badges[badge_id] = {"name": badge_data["name"], "description": badge_data["description"], "image": badge_data["image"]}
            else:
                continue
        elif badge_data["certified"]:
            if certified:
                all_badges[badge_id] = {"name": badge_data["name"], "description": badge_data["description"], "image": badge_data["image"]}
            else:
                continue
        else:
            all_badges[badge_id] = {"name": badge_data["name"], "description": badge_data["description"], "image": badge_data["image"]}
    return all_badges
