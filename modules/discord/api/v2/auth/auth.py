from modules.core import *
from .models import APIResponse, Login, LoginInfo, OAuthInfo, LoginResponse, LoginBan, BaseUser, Callback
from ..base import API_VERSION
from urllib.parse import unquote

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
    id = uuid.uuid4()
    await redis_db.set(f"oauth-{id}", orjson.dumps({
        "scopes": data.scopes, 
        "redirect": data.redirect if data.redirect else "/", 
        "callback": data.callback.dict()
    }), ex = 90)
    return api_success(url = discord_o.get_discord_oauth(id, data.scopes))

@router.get("/auth/callback")
async def auth_callback_handler(request: Request, code: str, state: str):
    oauth = await redis_db.get(f"oauth-{state}")
    if not oauth:
        return api_error(
            "Invalid state. There is no oauth data associated with this state. Please try and login again"        
        )
    oauth = orjson.loads(oauth)
    callback = Callback(**oauth["callback"])
    try:
        client = enums.KnownClients(callback.name)
        if client.__key__ != callback.key:
            return api_error(
                "Invalid client key for known client"
            )
    except ValueError:
        client = enums.KnownClients.unknown
        
    url = f"{callback.url}?code={code}&scopes={discord_o.get_scopes(oauth['scopes'])}&redirect={oauth['redirect']}
    
    if not callback.url.startswith("http://localhost:"):
        async with aiohttp.ClientSession() as sess:
            async with sess.put(callback.url, headers = {"Snowfall": callback.verify_key}):
                if res.status_code != 200:
                    return api_error(
                        "Callback URL does not return 200 on PUT!"
                    )
                try:
                    json = await res.json()
                except Exception:
                    return api_error(
                        "Callback URL not returning a proper JSON"
                    )
                if json.get("key", "") != callback.key or json.get("name", "") != callback.name:
                    return api_error(
                        "Callback URL not returning name in performed oauth request"
                    )
    if client.__noprompt__:
        return RedirectResponse(url)
    return api_error(
        "Prompt auth is not yet implemented!"
    )

@router.post("/users", response_model = LoginResponse)
async def login_user(request: Request, data: Login):
    try:
        access_token = await discord_o.get_access_token(data.code, "%20".join(data.scopes))
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

