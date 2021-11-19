from lxml.html.clean import Cleaner

from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io, textwrap, aiofiles
from starlette.concurrency import run_in_threadpool
from math import floor

from ..base import API_VERSION
from .models import APIResponse, Guild, GuildRandom, BotStats, BotEvents

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/guilds",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Servers"],
    dependencies=[Depends(id_check("guild"))]
)


from colour import Color

def is_color_like(c):
    try:
        # Converting 'deep sky blue' to 'deepskyblue'
        color = c.replace(" ", "")
        Color(color)
        # if everything goes fine then return True
        return True
    except ValueError: # The color code was not found
        return False


#@router.get("/{bot_id}/vpm")
async def get_votes_per_month(request: Request, bot_id: int):
    return await db.fetch("SELECT votes, epoch FROM bot_stats_votes_pm WHERE bot_id = $1", bot_id)

#@router.get("/{bot_id}/tv")
async def get_total_votes(request: Request, bot_id: int):
    return await db.fetchrow("SELECT total_votes AS votes FROM bot_stats_votes WHERE bot_id = $1", bot_id)

@router.patch(
    "/{guild_id}/token", 
    response_model = APIResponse, 
    dependencies = [
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, minutes=3)
            )
        ), 
        Depends(server_auth_check)
    ],
    operation_id="regenerate_server_token"
)
async def regenerate_server_token(request: Request, guild_id: int):
    """
    Regenerates a server token. Use this if it is compromised and you don't have time to use slash commands
    

    Example:

    ```py
    import requests

    def regen_token(guild_id, token):
        res = requests.patch(f"https://fateslist.xyz/api/v2/bots/{guild_id}/token", headers={"Authorization": f"Server {token}"})
        json = res.json()
        if not json["done"]:
            # Handle failures
            ...
        return res, json
    ```
    """
    await db.execute("UPDATE servers SET api_token = $1 WHERE guild_id = $2", get_token(256), guild_id)
    return api_success()

@router.get(
    "/{guild_id}/random", 
    response_model = GuildRandom, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, seconds=5),
                operation_bucket="random_guild"
            )
        )
    ],
    operation_id="fetch_random_server"
)
async def fetch_random_server(request: Request, guild_id: int, lang: str = "default"):
    """
    Fetch a random server. Server ID should be the recursive/root server 0.


    Example:
    ```py
    import requests

    def random_server():
        res = requests.get("https://fateslist.xyz/api/guilds/0/random")
        json = res.json()
        if not json.get("done", True):
            # Handle an error in the api
            ...
        return res, json
    ```
    """
    if guild_id != 0:
        return api_error(
            "This guild cannot use the fetch random guild API"
        )

    random_unp = await db.fetchrow(
        "SELECT description, banner_card, state, votes, guild_count, guild_id FROM servers WHERE (state = 0 OR state = 6) AND description IS NOT NULL ORDER BY RANDOM() LIMIT 1"
    ) # Unprocessed, use the random function to get a random bot
    bot_obj = await db.fetchrow("SELECT name_cached AS username, avatar_cached AS avatar FROM servers WHERE guild_id = $1", random_unp["guild_id"])
    bot_obj = dict(bot_obj) | {"disc": "0000", "status": 1, "bot": True}
    bot = bot_obj | dict(random_unp) # Get bot from cache and add that in
    bot["guild_id"] = str(bot["guild_id"]) # Make sure bot id is a string to prevent corruption issues in javascript
    bot["formatted"] = {
        "votes": human_format(bot["votes"]),
        "guild_count": human_format(bot["guild_count"])
    }
    bot["description"] = cleaner.clean_html(intl_text(bot["description"], lang)) # Prevent XSS attacks in short description
    if not bot["banner_card"]: # Ensure banner is always a string
        bot["banner_card"] = "" 
    return bot

@router.get(
    "/{guild_id}", 
    response_model = Guild, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=2),
                operation_bucket="fetch_guild"
            )
        )
    ],
    operation_id="fetch_server"
)
async def fetch_server(
    request: Request, 
    guild_id: int, 
    compact: Optional[bool] = True, 
    no_cache: Optional[bool] = False
):
    """
    Fetches server information given a server/guild ID. If not found, 404 will be returned.
    
    Setting compact to true (default) -> description, long_description, long_description_type, keep_banner_decor and css will be null

    No cache means cached responses will not be served (may be temp disabled in the case of a DDOS or temp disabled for specific servers as required)
    """
    if len(str(guild_id)) not in [17, 18, 19, 20]:
        return abort(404)

    if not no_cache:
        cache = await redis_db.get(f"guildcache-{guild_id}")
        if cache:
            return orjson.loads(cache)
    

    api_ret = await db.fetchrow(
        "SELECT banner_card, banner_page, guild_count, invite_amount, state, website, votes, invite_channel, nsfw FROM servers WHERE guild_id = $1", 
        guild_id
    )
    if api_ret is None:
        return abort(404)

    api_ret = dict(api_ret)

    api_ret["invite_channel"] = str(api_ret["invite_channel"])

    if not compact:
        extra = await db.fetchrow(
            "SELECT description, long_description_type, long_description, css, keep_banner_decor FROM servers WHERE guild_id = $1",
            guild_id
        )
        api_ret |= dict(extra)

    api_ret["tags"] = [dict(d) for d in (await db.fetch("SELECT tag, emoji FROM server_tags WHERE guild_id = $1", guild_id))]
   
    api_ret["user"] = dict((await db.fetchrow("SELECT guild_id AS id, name_cached AS username, '#0000' AS disc, avatar_cached AS avatar FROM servers WHERE guild_id = $1", guild_id)))
    
    api_ret["vanity"] = await db.fetchval(
        "SELECT vanity_url FROM vanity WHERE redirect = $1 AND type = 0", 
        guild_id
    )

    await redis_db.set(f"guildcache-{guild_id}", orjson.dumps(api_ret), ex=60*60*8)

    return api_ret


@router.head("/{guild_id}", operation_id="server_exists")
async def server_exists(request: Request, guild_id: int):
    count = await db.fetchval("SELECT guild_id FROM servers WHERE guild_id = $1", guild_id)
    return PlainTextResponse("", status_code=200 if count else 404) 


@router.get("/{guild_id}/widget", operation_id="get_server_widget")
async def server_widget(request: Request, bt: BackgroundTasks, guild_id: int, format: enums.WidgetFormat, bgcolor: Union[int, str] ='black', textcolor: Union[int, str] ='white'):
    """
    Returns a widget
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
    
    bot = await db.fetchrow("SELECT guild_count, votes, description FROM servers WHERE guild_id = $1", guild_id)
    if not bot:
        return abort(404)
   
    bt.add_task(add_ws_event, guild_id, {"m": {"e": enums.APIEvents.server_view}, "ctx": {"user": request.session.get('user_id'), "widget": True}}, type = "server")
    data = {"bot": bot, "user": await db.fetchrow("SELECT name_cached AS username, avatar_cached AS avatar FROM servers WHERE guild_id = $1", guild_id)}
    bot_obj = data["user"]
    
    if not bot_obj:
        return abort(404)

    if format == enums.WidgetFormat.json:
        return data
    
    elif format == enums.WidgetFormat.html:
        return await templates.TemplateResponse("widget.html", {"request": request} | data)
    
    elif format in (enums.WidgetFormat.png, enums.WidgetFormat.webp):
        # Check if in cache
        cache = await redis_db.get(f"widget-{guild_id}-{format.name}-{textcolor}")
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
        await redis_db.set(f"widget-{guild_id}-{format.name}-{textcolor}", output.read(), ex=60*3)
        output.seek(0)

        def _stream():    
            yield from output
            output.close()

        return StreamingResponse(_stream(), media_type=f"image/{format.name}")

@router.get(
    "/{guild_id}/ws_events",
    dependencies = [
        Depends(server_auth_check)
    ],
    operation_id="get_server_ws_events"
)
async def get_server_ws_events(request: Request, guild_id: int):
    events = await redis_db.hget(f"server-{guild_id}", key = "ws")
    if events is None:
        events = {} # Nothing
    return orjson.loads(events) 
    
