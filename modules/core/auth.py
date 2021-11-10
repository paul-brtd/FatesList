from .imports import *
from fastapi import Security
from fastapi.security.api_key import APIKeyQuery, APIKeyCookie, APIKeyHeader, APIKey

bot_auth_header = APIKeyHeader(name="Authorization", description="These endpoints require a bot token. You can get this from Bot Settings. Make sure to keep this safe and in a .gitignore/.env.\n\nA prefix of `Bot` before the bot token such as `Bot abcdef` is supported and can be used to avoid ambiguity but is not required. The default auth scheme if no prefix is given depends on the endpoint: Endpoints which have only one auth scheme will use that auth scheme while endpoints with multiple will always use `Bot` for backward compatibility", scheme_name="Bot")

user_auth_header = APIKeyHeader(name="Authorization", description="These endpoints require a user token. You can get this from your profile under the User Token section. If you are using this for voting, make sure to allow users to opt out!\n\nA prefix of `User` before the user token such as `User abcdef` is supported and can be used to avoid ambiguity but is not required outside of endpoints that have both a user and a bot authentication option such as Get Votes. In such endpoints, the default will always be a bot auth unless you prefix the token with `User`", scheme_name="User")

async def _bot_auth(bot_id: int, api_token: str):
    return await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))

async def _user_auth(user_id: int, api_token: str):
    if isinstance(user_id, int):
        pass
    elif user_id.isdigit():
        user_id = int(user_id)
    else:
        return None
    return await db.fetchval("SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))

async def bot_auth_check(bot_id: int, bot_auth: str = Security(bot_auth_header)):
    if bot_auth.startswith("Bot "):
        bot_auth = bot_auth.replace("Bot ", "", 1)
    id = await _bot_auth(bot_id, bot_auth)
    if id is None:
        raise HTTPException(status_code=401, detail="Invalid Bot Token")

async def user_auth_check(request: Request, user_id: int, user_auth: str = Security(user_auth_header)):
    if user_auth.startswith("User "):
        user_auth = user_auth.replace("User ", "", 1)
    id = await _user_auth(user_id, user_auth)
    if id is None:
        raise HTTPException(status_code=401, detail=f"Invalid User Token for route {request.url.path} and IP {request.client.host}")

async def bot_user_auth_check(bot_id: int, user_id: Optional[int] = None, bot_auth: str = Security(bot_auth_header), user_auth: str = Security(user_auth_header)):
    if user_auth.startswith("User "):
        scheme = "User"
        id = await _user_auth(user_id, user_auth)
    else:
        scheme = "Bot"
        id = await _bot_auth(bot_id, bot_auth)
    
    if not id:
        raise HTTPException(status_code=401, detail=f"Invalid {scheme} Token")
