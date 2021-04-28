from .imports import *

async def bot_auth(bot_id: int, api_token: str, *, fields: Optional[str] = None):
    if fields is None:
        return await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))
    return await db.fetchrow(f"SELECT bot_id, {fields} FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))

async def user_auth(user_id: int, api_token: str, fields: Optional[str] = None):
    try:
        user_id = int(user_id)
    except:
        return None
    if fields is None:
        return await db.fetchval("SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))
    return await db.fetchrow(f"SELECT user_id, {fields} FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))

async def get_user_token(uid: int, username: str) -> str:
    token = await db.fetchrow("SELECT username, api_token FROM users WHERE user_id = $1", int(uid))
    if token is None:
        flag = True
        while flag:
            token = get_token(101)
            tcheck = await db.fetchrow("SELECT api_token FROM users WHERE api_token = $1", token)
            if tcheck is None:
                flag = False
        await db.execute("INSERT INTO users (user_id, api_token, vote_epoch, username) VALUES ($1, $2, $3, $4)", int(uid), token, None, username)
    else:
        # Update their username if needed
        if token["username"] != username:
            await db.execute("UPDATE users SET username = $1 WHERE user_id = $2", username, int(uid))
        token = token["api_token"]
        return token
