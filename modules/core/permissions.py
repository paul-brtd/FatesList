"""
Permission Related Code
"""

from .imports import *


class StaffMember(BaseModel):
    """Represents a staff member in Fates List""" 
    name: str
    id: Union[str, int]
    perm: int
    staff_id: Union[str, int]

async def is_staff_unlocked(bot_id: int, user_id: int):
    return await redis_db.exists(f"fl_staff_access-{user_id}:{bot_id}")

async def is_bot_admin(bot_id: int, user_id: int):
    try:
        user_id = int(user_id)
    except ValueError:
        return False
    guild = client.get_guild(main_server)
    try:
        user = guild.get_member(user_id)
    except:
        user = None
    if user is not None and is_staff(staff_roles, user.roles, 4)[0] and (await is_staff_unlocked(bot_id, user_id)):
        return True
    check = await db.fetchval("SELECT COUNT(1) FROM bot_owner WHERE bot_id = $1 AND owner = $2", bot_id, user_id)
    if check == 0:
        return False
    return True

# Internal backend entry to check if one role is in staff and return a dict of that entry if so
def _get_staff_member(staff_json: dict, role: int) -> StaffMember:
    for key in staff_json.keys(): # Loop through all keys in staff json
        if int(role) == int(staff_json[key]["id"]): # Check if role matches
            return StaffMember(name = key, id = str(staff_json[key]["id"]), staff_id = str(staff_json[key]["staff_id"]), perm = staff_json[key]["perm"]) # Return the staff json role data
    return StaffMember(name = "user", id = str(staff_json["user"]["id"]), staff_id = str(staff_json["user"]["staff_id"]), perm = 1) # Fallback to perm 1 user member

def is_staff(staff_json: dict, roles: Union[list, int], base_perm: int) -> Union[bool, int, StaffMember]:
    if type(roles) != list and type(roles) != tuple:
        roles = [roles]
    max_perm = 0 # This is a cache of the max perm a user has
    sm = StaffMember(name = "user", id = str(staff_json["user"]["id"]), staff_id = str(staff_json["user"]["staff_id"]), perm = 1) # Initially
    bak_sm = sm # Backup staff member
    for role in roles: # Loop through all roles
        if type(role) == discord.Role:
            role = role.id
        sm = _get_staff_member(staff_json, role)
        if sm.perm > max_perm:
            max_perm = sm.perm
            bak_sm = sm # Back it up so it doesnt get overwritten
    if max_perm >= base_perm:
        return True, max_perm, bak_sm # Use backup and not overwritten one
    return False, max_perm, sm # Use normal one
