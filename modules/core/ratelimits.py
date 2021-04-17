from .imports import *

async def rl_key_func(request: Request) -> str:
    if secure_strcmp(request.headers.get("FatesList-RateLimitBypass"), ratelimit_bypass_key): # Check ratelimit key
        return get_token(32) # Disable since bypassed
    if "Authorization" in request.headers or "authorization" in request.headers:
        try: # Check for auth header
            r = request.headers["Authorization"]
        except KeyError:
            r = request.headers["authorization"]
        check = await db.fetchrow("SELECT bot_id, state FROM bots WHERE api_token = $1", r) # Check api token
        if check is None:
            return ip_check(request) # Invalid api token, fallback to ip
        if check["state"] == enums.BotState.certified:
            return get_token(32) # Disable since certified bots are exempt
        return str(check["bot_id"]) # Otherwise, ratelimit using bot id
    else:
        return ip_check(request) # Fallback to ip
