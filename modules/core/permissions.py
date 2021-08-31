"""
Permission Related Code
"""

from .imports import *
from .helpers import *

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
    if (await is_staff(staff_roles, user_id, 4))[0] and (await is_staff_unlocked(bot_id, user_id)):
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

async def is_staff(staff_json: dict, user_id: int, base_perm: int, json: bool = False, *, redis=None) -> Union[bool, int, StaffMember]:
    redis = redis if redis else redis_db
    max_perm = 0 # This is a cache of the max perm a user has
    sm = StaffMember(name = "user", id = str(staff_json["user"]["id"]), staff_id = str(staff_json["user"]["staff_id"]), perm = 1) # Initially
    bak_sm = sm # Backup staff member
    roles = await redis_ipc_new(redis, "ROLES", args=[str(user_id)])
    if roles == b"-1":
        if json:
            return False, 1, sm.dict()
        return False, 1, sm
    if not roles:
        return False, 1, sm.dict()
    roles = roles.decode("utf-8").split(" ")
    for role in roles: # Loop through all roles
        sm = _get_staff_member(staff_json, role)
        if sm.perm > max_perm:
            max_perm = sm.perm
            bak_sm = sm # Back it up so it doesnt get overwritten
    if max_perm >= base_perm:
        if json:
            return True, max_perm, bak_sm.dict()
        return True, max_perm, bak_sm # Use backup and not overwritten one
    if json:
        return False, max_perm, sm.dict()
    return False, max_perm, sm # Use normal one
