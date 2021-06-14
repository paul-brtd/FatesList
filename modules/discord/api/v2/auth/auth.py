from modules.core import *
from .models import APIResponse, Login
from ..base import API_VERSION

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/auth",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Auth"]
)

discord_o = Oauth(OauthConfig)

@router.get("/login")
async def get_login_link(request: Request, scopes: List[str], redirect: Optional[str] = None):
    if redirect:
        if not redirect.startswith("/") and not redirect.startswith("https://fateslist.xyz"):
            return api_error(
                "Invalid redirect. You may only redirect to pages on Fates List"
            )
    oauth_data = discord_o.get_discord_oauth(scopes, redirect if redirect else "/")
    return api_success(url = oauth_data["url"])

@router.put("/login")
async def login_user(request: Request, data: Login):
    try:
        access_token = await discord_o.get_access_token(data.code, " ".join(data.scopes))
        userjson = await discord_o.get_user_json(access_token["access_token"])
    except:
        return api_error(
            "We have encountered an issue while logging you in (could not create user json)...",
            banned = False
        )
    
    user_info = await db.fetchrow(
        "SELECT state, api_token, username FROM users WHERE user_id = $1", 
        int(userjson["id"])
    )
    
    if user_info["state"] is None:
        token = get_token(101) 
        await db.execute(
            "DELETE FROM users WHERE user_id = $1", 
            int(userjson["id"])
        ) # Delete any potential existing but corrupt data

        await db.execute(
            "INSERT INTO users (user_id, username, api_token) VALUES ($1, $2, $3)", 
            int(userjson["id"]), 
            userjson["name"], 
            token
        )

        css, state = None, 0

    else:
        state = enums.UserState(user_info["state"])
        if state.__sitelock__:
            ban_data = bans_data[str(state)]
            return api_error(
                "You have been banned from Fates List",
                banned = True,
                ban = {
                    "type": ban_data["type"],
                    "desc": ban_data["desc"]
                },
                state = state
            )
        if userjson["name"] != user_info["username"]:
            await db.execute(
                "UPDATE users SET username = $1", 
                userjson["name"]
            ) 

        token, css, state = user_info["api_token"], user_info["css"] if user_info["css"] else None, state

    if userjson["avatar"]:
        avatar = f'https://cdn.discordapp.com/avatars/{userjson["id"]}/{userjson["avatar"]}'
    else:
        avatar = "https://s3.us-east-1.amazonaws.com/files.tvisha.aws/posts/crm/panel/attachments/1580985653/discord-logo.jpg"

    return api_success(
        id = userjson["id"],
        username = userjson["name"],
        avatar = avatar,
        token = token,
        css = css,
        state = state,
        redirect = data.redirect
    )

