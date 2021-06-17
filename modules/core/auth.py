from .imports import *

async def bot_auth(bot_id: int, api_token: str):
    return await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))

async def user_auth(user_id: int, api_token: str):
    if isinstance(user_id, int):
        pass
    elif user_id.isdigit():
        user_id = int(user_id)
    else:
        return None
    return await db.fetchval("SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))

async def bot_auth_check(bot_id: int, Authorization: str = Header("Put Bot Token Here")):
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        raise HTTPException(status_code=401, detail="Invalid Bot Token")
