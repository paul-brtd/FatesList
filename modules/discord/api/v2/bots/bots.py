from lxml.html.clean import Cleaner

from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io, textwrap, aiofiles
from starlette.concurrency import run_in_threadpool
from matplotlib.colors import is_color_like
from math import floor

from ..base import API_VERSION
from .models import APIResponse, Bot, BotRandom, BotStats, BotEvents

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Bots"],
    dependencies=[Depends(id_check("bot"))]
)

@router.get("/{bot_id}/vpm")
async def get_votes_per_month(request: Request, bot_id: int):
    return await db.fetch("SELECT votes, epoch FROM bot_stats_votes_pm WHERE bot_id = $1", bot_id)

@router.get("/{bot_id}/tv")
async def get_total_votes(request: Request, bot_id: int):
    return await db.fetchrow("SELECT total_votes AS votes FROM bot_stats_votes WHERE bot_id = $1", bot_id)

@router.patch(
    "/{bot_id}/token", 
    response_model = APIResponse, 
    dependencies = [
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, minutes=3)
            )
        ), 
        Depends(bot_auth_check)
    ],
    operation_id="regenerate_bot_token"
)
async def regenerate_bot_token(request: Request, bot_id: int):
    """
    Regenerates a bot token. Use this if it is compromised
    

    Example:

    ```py
    import requests

    def regen_token(bot_id, token):
        res = requests.patch(f"https://fateslist.xyz/api/v2/bots/{bot_id}/token", headers={"Authorization": f"Bot {token}"})
        json = res.json()
        if not json["done"]:
            # Handle failures
            ...
        return res, json
    ```
    """
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(132), bot_id)
    return api_success()

@router.get(
    "/{bot_id}/random", 
    response_model = BotRandom, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, seconds=5),
                operation_bucket="random_bot"
            )
        )
    ],
    operation_id="fetch_random_bot"
)
async def fetch_random_bot(request: Request, bot_id: int, lang: str = "default"):
    """
    Fetch a random bot. Bot ID should be the recursive/root bot 0


    Example:
    ```py
    import requests

    def random_bot():
        res = requests.get("https://fateslist.xyz/api/bots/0/random")
        json = res.json()
        if not json.get("done", True):
            # Handle an error in the api
            ...
        return res, json
    ```
    """
    if bot_id != 0:
        return api_error(
            "This bot cannot use the fetch random bot API"
        )

    random_unp = await db.fetchrow(
        "SELECT description, banner_card, state, votes, guild_count, bot_id, invite FROM bots WHERE state = 0 OR state = 6 ORDER BY RANDOM() LIMIT 1"
    ) # Unprocessed, use the random function to get a random bot
    bot_obj = await get_bot(random_unp["bot_id"], worker_session = request.app.state.worker_session)
    if bot_obj is None or bot_obj["disc"] == "0000":
        return await fetch_random_bot(request, lang) # Get a new bot
    bot = bot_obj | dict(random_unp) # Get bot from cache and add that in
    bot["bot_id"] = str(bot["bot_id"]) # Make sure bot id is a string to prevent corruption issues in javascript
    bot["formatted"] = {
        "votes": human_format(bot["votes"]),
        "guild_count": human_format(bot["guild_count"])
    }
    bot["description"] = cleaner.clean_html(intl_text(bot["description"], lang)) # Prevent XSS attacks in short description
    if not bot["banner_card"]: # Ensure banner is always a string
        bot["banner_card"] = "" 
    return bot

@router.get(
    "/{bot_id}", 
    response_model = Bot, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=2),
                operation_bucket="fetch_bot"
            )
        )
    ],
    operation_id="fetch_bot"
)
async def fetch_bot(
    request: Request, 
    bot_id: int, 
    compact: Optional[bool] = True, 
    offline: Optional[bool] = False,
):
    """
    Fetches bot information given a bot ID. If not found, 404 will be returned.
    
    Setting compact to true (default) -> description, long_description, long_description_type, keep_banner_decor and css will be null

    Setting offline to true -> user will be null and no ownership info will be given. If the bot is no longer on discord, this endpoint will still return if offline is set to true
    """
    if len(str(bot_id)) not in [17, 18, 19, 20]:
        return abort(404)
    
    check = await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1", bot_id)
    if not check:
        return abort(404)

    api_ret = await db.fetchrow(
        "SELECT last_stats_post, banner_card, banner_page, guild_count, shard_count, shards, prefix, invite, invite_amount, features, bot_library AS library, state, website, discord AS support, github, user_count, votes, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", 
        bot_id
    )
    api_ret = dict(api_ret)
    if not compact:
        extra = await db.fetchrow(
            "SELECT description, long_description_type, long_description, css, keep_banner_decor FROM bots WHERE bot_id = $1",
            bot_id
        )
        api_ret |= dict(extra)

    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    api_ret["tags"] = [tag["tag"] for tag in tags]
   
    if not offline:
        owners_db = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
        owners = []
        _done = []

        # Preperly sort owners
        for owner in owners_db:
            if owner in _done: continue
        
            _done.append(owner["owner"])
            user = await get_user(owner["owner"])
            main = owner["main"]

            if not user: continue
        
            owner_obj = {
                "user": user,
                "main": main
            }
        
            if main: owners.insert(0, owner_obj)
            else: owners.append(owner_obj)

        api_ret["owners"] = owners
    
    api_ret["features"] = api_ret["features"]
    api_ret["invite_link"] = await invite_bot(bot_id, api = True)
    
    if not offline:
        api_ret["user"] = await get_bot(bot_id)
        if not api_ret["user"]:
            return abort(404)
    
    api_ret["vanity"] = await db.fetchval(
        "SELECT vanity_url FROM vanity WHERE redirect = $1", 
        bot_id
    )
    return api_ret


@router.head("/{bot_id}", operation_id="bot_exists")
async def bot_exists(request: Request, bot_id: int):
    count = await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1", bot_id)
    return PlainTextResponse("", status_code=200 if count else 404) 


@router.get("/{bot_id}/widget", operation_id="get_bot_widget")
async def bot_widget(request: Request, bt: BackgroundTasks, bot_id: int, format: enums.WidgetFormat, bgcolor: int | str ='black', textcolor: int | str ='white'):
    """
    Returns a widget

    Unstable signifies whether an action is unstable or not. You will get a API error if this is the case and unstable is not set or the bot is not certified (only certified bots may use unstable endpoints) and the existence of the nyi key can be used to programatically detect this
    """
    if not is_color_like(str(bgcolor)) or not is_color_like(str(textcolor)):
        return abort(404)
    if isinstance(bgcolor, str):
        bgcolor=bgcolor.split('.')[0]
        bgcolor = floor(int(bgcolor)) if bgcolor.isdigit() or bgcolor.isdecimal() else bgcolor
    if isinstance(textcolor, str):
        textcolor=textcolor.split('.')[0]
        textcolor = floor(int(textcolor)) if textcolor.isdigit() or textcolor.isdecimal() else textcolor
        
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    
    bot = await db.fetchrow("SELECT guild_count, votes, description FROM bots WHERE bot_id = $1", bot_id)
    if not bot:
        return abort(404)
    
    bt.add_task(add_ws_event, bot_id, {"m": {"e": enums.APIEvents.bot_view}, "ctx": {"user": request.session.get('user_id'), "widget": True}})
    data = {"bot": bot, "user": await get_bot(bot_id, worker_session = request.app.state.worker_session)}
    bot_obj = data["user"]
    
    if not bot_obj:
        return abort(404)

    if format == enums.WidgetFormat.json:
        return data
    
    elif format == enums.WidgetFormat.html:
        return await templates.TemplateResponse("widget.html", {"request": request} | data)
    
    elif format in (enums.WidgetFormat.png, enums.WidgetFormat.webp):
        # Check if in cache
        cache = await redis_db.get(f"widget-{bot_id}-{format.name}-{textcolor}")
        if cache:
            def _stream():
                with io.BytesIO(cache) as output:
                    yield from output

            return StreamingResponse(_stream(), media_type=f"image/{format.name}")

        widget_img = Image.new("RGBA", (300, 175), bgcolor)
        async with aiohttp.ClientSession() as sess:
            async with sess.get(data["user"]["avatar"]) as res:
                avatar_img = await res.read()

        static = request.app.state.static
        fates_pil = static["fates_pil"]
        votes_pil = static["votes_pil"]
        server_pil = static["server_pil"]
        avatar_pil = Image.open(io.BytesIO(avatar_img)).resize((100, 100))
        avatar_pil_bg = Image.new('RGBA', avatar_pil.size, (0,0,0))
            
        #pasting the bot image
        try:
            widget_img.paste(Image.alpha_composite(avatar_pil_bg, avatar_pil),(10,widget_img.size[-1]//5))
        except:
            widget_img.paste(avatar_pil,(10,widget_img.size[-1]//5))
            
        def remove_transparency(im, bgcolor):
            if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
                alpha = im.convert('RGBA').split()[-1]
                
                # Create a new background image of our matt color.
                # Must be RGBA because paste requires both images have the same format
                # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
                bg = Image.new("RGBA", im.size, bgcolor)
                bg.paste(im, mask=alpha)
                return bg
            else:
                return im
        widget_img.paste(remove_transparency(fates_pil, bgcolor),(10,152))
        
        #pasting votes logo
        try:
            widget_img.paste(Image.alpha_composite(avatar_pil_bg, votes_pil),(120,115))
        except:
            widget_img.paste(votes_pil,(120,115))
        
        #pasting servers logo
        try:
            widget_img.paste(Image.alpha_composite(avatar_pil_bg, server_pil),(120,95))
        except:
            widget_img.paste(server_pil,(120,95))

        font = os.path.join("data/static/LexendDeca-Regular.ttf")

        def get_font(string: str, d):
            return ImageFont.truetype(
                font,
                get_font_size(d.textsize(string)[0]),
                layout_engine=ImageFont.LAYOUT_RAQM
            )
        
        def get_font_size(width: int):
            if width <= 90:
                return 18  
            elif width >= 192:
                return 10
            elif width == 168:
                return 12
            else:
                return 168-width-90
        
        def the_area(str_width: int, image_width: int):
            if str_width < 191:
                new_width=abs(int(str_width-image_width))
                return (new_width//2.5)
            else:
                new_width=abs(int(str_width-image_width))
                return (new_width//4.5)
                
         
        #lists name
        d = ImageDraw.Draw(widget_img)
        d.text(
            (25,150), 
            str('Fates List'), 
            fill=textcolor,
            font=ImageFont.truetype(
                font,
                10,
                layout_engine=ImageFont.LAYOUT_RAQM
            )
        )

        #Bot name
        d.text(
            (
                the_area(
                    d.textsize(str(bot_obj['username']))[0],
                    widget_img.size[0]
                ),
                5
            ), 
            str(bot_obj['username']), 
            fill=textcolor,
            font=ImageFont.truetype(
                font,
                16,
                layout_engine=ImageFont.LAYOUT_RAQM
                )
            )
        
        #description
        wrapper = textwrap.TextWrapper(width=30)
        word_list = wrapper.wrap(text=bot['description'])
        d.text(
            (120,30), 
            str('\n'.join(word_list)), 
            fill=textcolor,
            font=get_font(str(bot['description']),d)
        )
        
        #server count
        d.text(
            (140,94), 
            human_format(bot["guild_count"]), 
            fill=textcolor,
            font=get_font(human_format(bot["guild_count"]),d)
        )
        
        #votes
        d.text(
            (140,114),
            human_format(bot["votes"]), 
            fill=textcolor,
            font=get_font(human_format(bot['votes']),d)
        )
            
        output = io.BytesIO()
        widget_img.save(output, format=format.name.upper())
        output.seek(0)
        await redis_db.set(f"widget-{bot_id}-{format.name}-{textcolor}", output.read(), ex=60*3)
        output.seek(0)

        def _stream():    
            yield from output
            output.close()

        return StreamingResponse(_stream(), media_type=f"image/{format.name}")

@router.get(
    "/{bot_id}/events", 
    response_model = BotEvents,
    dependencies = [
        Depends(bot_auth_check)
    ],
    operation_id="get_bot_events",
    deprecated=True
)
async def get_bot_events(request: Request, bot_id: int, exclude: Optional[str] = None, filter: Optional[str] = None):
    """Get bot events, all exclude and filters must be comma seperated. This has been replaced by Get WS Events for most use cases"""
    exclude = exclude.split(",")
    filter = filter.split(",")
    return await bot_get_events(bot_id = bot_id, filter = filter, exclude = exclude)

@router.get(
    "/{bot_id}/ws_events",
    dependencies = [
        Depends(bot_auth_check)
    ],
    operation_id="get_bot_ws_events"
)
async def get_bot_ws_events(request: Request, bot_id: int):
    ini_events = {}
    events = await redis_db.hget(f"{type}-{bot_id}", key = "ws")
    if events is None:
        events = {} # Nothing
    return events 
    

@router.post(
    "/{bot_id}/stats", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1),
                operation_bucket="set_bot_stats"
            ) 
        ),
        Depends(bot_auth_check)
    ],
    operation_id="set_bot_stats"
)
async def set_bot_stats(request: Request, bot_id: int, api: BotStats):
    """
    This endpoint allows you to set the guild + shard counts for your bot


    Example:
    ```py
    # This will use aiohttp and not requests as this is likely to used by discord.py bots
    import aiohttp


    # On dpy, guild_count is usually the below
    guild_count = len(client.guilds)

    # If you are using sharding
    shard_count = len(client.shards)
    shards = client.shards.keys()

    # Optional: User count (this is not accurate for larger bots)
    user_count = len(client.users) 

    async def set_stats(bot_id, token, guild_count, shard_count = None, shards = None, user_count = None):
        json = {"guild_count": guild_count, "shard_count": shard_count, "shards": shards, "user_count": user_count}

        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"https://fateslist.xyz/api/bots/{bot_id}/stats", headers={"Authorization": f"Bot {token}"}, json=json) as res:
                json = await res.json()
                if not json["done"]:
                    # Handle or log this error
                    ...
    ```
    """
    stats_old = await db.fetchrow(
        "SELECT guild_count, shard_count, shards, user_count FROM bots WHERE bot_id = $1",
        bot_id
    )
    stats_new = api.dict()
    stats = {}
    for stat in stats_new.keys():
        if stats_new[stat] is None:
            stats[stat] = stats_old[stat]
        else:
            stats[stat] = stats_new[stat]
    await set_stats(bot_id = bot_id, **stats)
    return api_success()