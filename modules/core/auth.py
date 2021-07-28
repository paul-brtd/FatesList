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

async def user_auth_check(user_id: int, Authorization: str = Header("Put User Token Here")):
    id = await user_auth(user_id, Authorization)
    if id is None:
        raise HTTPException(status_code=401, detail="Invalid User Token")

async def bot_user_auth_check(bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("Put Bot Token or User Token here")):
    id = None
    
    if user_id:
        id = await user_auth(user_id, Authorization)
    
    if not id:
        id = await bot_auth(bot_id, Authorization)
    
        if not id: # Still
            raise HTTPException(status_code=401, detail="Invalid Bot Token or User Token")

async def manager_check(
    request: Request, 
    Authorization: str = Header("Put Manager Key Here"), 
    Lynx: int = Header("User ID of moderator"), 
    Snowfall: str = Header("Put User Token of moderator here")
):
    if not secure_strcmp(Authorization, manager_key):
        raise HTTPException(
            status_code=401, 
            detail="Invalid manager key",
        )

    id = await user_auth(Lynx, Snowfall)
    if id is None:
        raise HTTPException(
            "Snowfall/Lynx header mismatch. Please run +usertoken again to reset it",
            status_code=403
        )

    await client.wait_until_ready()
    guild = client.get_guild(main_server)
    request.state.user = guild.get_member(Lynx)
