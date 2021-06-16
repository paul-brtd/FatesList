from modules.core import *
from .models import APIResponse, Login, LoginInfo, OAuthInfo, LoginResponse, LoginBan, BaseUser
from ..base import API_VERSION

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Auth"]
)

discord_o = Oauth(OauthConfig)

@router.post("/oauth", response_model = OAuthInfo)
async def get_login_link(request: Request, data: LoginInfo):
    if data.redirect:
        if not data.redirect.startswith("/") and not data.redirect.startswith("https://fateslist.xyz"):
            return api_error(
                "Invalid redirect. You may only redirect to pages on Fates List"
            )
    oauth_data = discord_o.get_discord_oauth(data.scopes, data.redirect if data.redirect else "/")
    return api_success(url = oauth_data["url"])

@router.post("/users", response_model = LoginResponse)
async def login_user(request: Request, data: Login):
    try:
        access_token = await discord_o.get_access_token(data.code, "%20".join(data.scopes), redirect_uri = data.oauth_redirect if data.oauth_redirect else None)
        userjson = await discord_o.get_user_json(access_token["access_token"])
        if not userjson["id"]:
            raise ValueError("Invalid user json")
    except Exception:
        return api_error(
            "We have encountered an issue while logging you in (could not create user json)...",
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
            ban_data = bans_data[str(state)]
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
        await discord_o.join_user(access_token["access_token"], userjson["id"])

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
        redirect = data.redirect.replace(site_url, ""),
        banned = False
    )

