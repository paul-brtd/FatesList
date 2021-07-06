from urllib.parse import unquote

from modules.core import *

from ..base import API_VERSION
from .models import (APIResponse, BaseUser, Callback, Login, LoginBan,
                     LoginInfo, LoginResponse, OAuthInfo)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Auth"]
)

@router.post("/oauth", response_model = OAuthInfo)
async def get_login_link(request: Request, data: LoginInfo, worker_session = Depends(worker_session)):
    oauth = worker_session.oauth
    if data.redirect:
        if not data.redirect.startswith("/") and not data.redirect.startswith("https://fateslist.xyz"):
            return api_error(
                "Invalid redirect. You may only redirect to pages on Fates List"
            )
    redirect = data.redirect if data.redirect else "/"
    url = await oauth.discord.get_auth_url(
        scopes,
        {"callback": data.callback.dict(), "site_redirect": redirect}
    )
    return api_success(url = url.url)

@router.get("/auth/callback")
async def auth_callback_handler(request: Request, code: str, state: str, worker_session = Depends(worker_session)):
    oauth = worker_session.oauth
    
    id = oauth.discord.get_state_id(state)
    
    if not id:
        return api_error(
            "Invalid state provided. Please try logging in again using https://fateslist.xyz/auth/login"
        )
    
    oauth = await oauth.discord.get_state(id)
    if not oauth:
        return api_error(
            "Invalid state. Your state has expired. Please try logging in again using https://fateslist.xyz/auth/login"        
        )
     
    callback = Callback(**oauth["callback"])
    site_redirect = oauth['site_redirect']
        
    url = f"{callback.url}?code={code}&state={state}&site_redirect={site_redirect}"
    
    return RedirectResponse(url)
    
@router.post("/users", response_model = LoginResponse)
async def login_user(request: Request, data: Login, worker_session = Depends(worker_session)):
    oauth = worker_session.oauth
    
    try:
        access_token = await oauth.discord.get_access_token(data.code, data.state, "https://fateslist.xyz/auth/login")
        userjson = await oauth.discord.get_user_json(access_token)
        if not userjson or not userjson.get("id"):
            raise ValueError("Invalid user json")
            
    except Exception as exc:
        return api_error(
            f"We have encountered an issue while logging you in ({exc})...",
            banned = False
        )
    
    user_info = await db.fetchrow(
        "SELECT state, api_token, css, js_allowed, username FROM users WHERE user_id = $1", 
        int(userjson["id"])
    )
    
    if not user_info or user_info["state"] is None:
        token = get_token(101) 
        await db.execute(
            "DELETE FROM users WHERE user_id = $1", 
            int(userjson["id"])
        ) # Delete any potential existing but corrupt data

        await db.execute(
            "INSERT INTO users (id, user_id, username, api_token) VALUES ($1, $1, $2, $3)", 
            int(userjson["id"]), 
            userjson["username"], 
            token
        )

        css, state, js_allowed = None, 0, True

    else:
        state = enums.UserState(user_info["state"])
        if state.__sitelock__:
            ban_data = bans_data[str(state.value)]
            return api_error(
                "You have been banned from Fates List",
                banned = True,
                ban = LoginBan(
                    type = ban_data["type"],
                    desc = ban_data["desc"],
                ),
                state = state
            )
        if userjson["username"] != user_info["username"]:
            await db.execute(
                "UPDATE users SET username = $1", 
                userjson["username"]
            ) 

        token, css, state, js_allowed = user_info["api_token"], user_info["css"] if user_info["css"] else None, state, user_info["js_allowed"]

    if userjson["avatar"]:
        avatar = f'https://cdn.discordapp.com/avatars/{userjson["id"]}/{userjson["avatar"]}.webp'
    else:
        _avatar_id = int(userjson['discriminator']) % 5
        avatar = f"https://cdn.discordapp.com/embed/avatars/{_avatar_id}.png"
    
    user = await get_user(int(userjson["id"]))

    if "guilds.join" in data.scopes:
        await oauth.discord.add_user_to_guild(access_token, userjson["id"], main_server, TOKEN_MAIN)

    return api_success(
        user = BaseUser(
            id = userjson["id"],
            username = userjson["username"],
            bot = False,
            disc = userjson["discriminator"],
            avatar = avatar,
            status = user["status"] if user else 0
        ),
        token = token,
        css = css,
        state = state,
        js_allowed = js_allowed,
        access_token = access_token,
        banned = False
    )

