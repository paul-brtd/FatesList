from lxml.html.clean import Cleaner

from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io, textwrap, aiofiles
from starlette.concurrency import run_in_threadpool
from ..base import API_VERSION
from .models import APIResponse, Bot, BotRandom, BotStats, BotAppeal

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Bots"],
    dependencies=[Depends(id_check("bot"))]
)

@router.get(
    "/{bot_id}/token",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )    
        ), 
        Depends(user_auth_check)
    ]
)
async def get_bot_token(request: Request, bot_id: int, user_id: int):
    """
    Gets a bot token given a user token. 401 = Invalid API Token, 403 = Forbidden (not owner of bot or staff)
    """
    bot_admin = await is_bot_admin(bot_id, user_id)
    if not bot_admin:
        return abort(403)
    return await db.fetchrow("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)

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
    ]
)
async def regenerate_bot_token(request: Request, bot_id: int):
    """
    Regenerates the Bot token
    **Bot Token**: You can get this by clicking your bot and clicking edit and clicking Show (under API Token section)
    """
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(132), bot_id)
    return api_success()

@router.get(
    "/{bot_id}/random", 
    response_model = BotRandom, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, seconds=5)
            )
        )
    ]
)
async def fetch_random_bot(request: Request, bot_id: int, lang: str = "default"):
    """Fetch a random bot. Bot ID should be the recursive/root bot 0"""
    if bot_id != 0:
        return api_error(
            "This bot cannot use the fetch random bot API"
        )

    random_unp = await db.fetchrow(
        "SELECT description, banner_card, state, votes, guild_count, bot_id, invite FROM bots WHERE state = 0 OR state = 6 ORDER BY RANDOM() LIMIT 1"
    ) # Unprocessed, use the random function to get a random bot
    bot_obj = await get_bot(random_unp["bot_id"], worker_session = request.app.state.worker_session)
    if bot_obj is None:
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
                global_limit = Limit(times=5, minutes=2)
            )
        )
    ]
)
async def fetch_bot(
    request: Request, 
    bot_id: int, 
    compact: Optional[bool] = True, 
    with_tags: Optional[bool] = False,
    with_owners: Optional[bool] = False,
    offline: Optional[bool] = False
):
    """
    Fetches bot information given a bot ID. If not found, 404 will be returned.
    
    Setting compact to true (default) -> description, long_description, long_description_type, keep_banner_decor and css will be null

    Setting with_tags to false -> tags will be null

    Setting with_owners to false -> owners will be null

    Setting offline to true -> user will be null. If the bot is no longer on discord, this endpoint will still return if offline is set to true
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

    if with_tags:
        tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
        api_ret["tags"] = [tag["tag"] for tag in tags]
   
    if with_owners:
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


@router.head("/{bot_id}")
async def bot_exists(request: Request, bot_id: int):
    count = await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1", bot_id)
    return PlainTextResponse("", status_code=200 if count else 404) 


@router.get("/{bot_id}/widget")
async def bot_widget(request: Request, bt: BackgroundTasks, bot_id: int, format: enums.WidgetFormat):
    """
    Returns a widget

    Unstable signifies whether an action is unstable or not. You will get a API error if this is the case and unstable is not set or the bot is not certified (only certified bots may use unstable endpoints) and the existence of the nyi key can be used to programatically detect this

    The webp format is unstable. All the others are stable
    """
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    
    bot = await db.fetchrow("SELECT bot_id, guild_count, votes, state, description FROM bots WHERE bot_id = $1", bot_id)
    if not bot:
        return abort(404)
    bot = dict(bot)
    
    bt.add_task(add_ws_event, bot_id, {"m": {"e": enums.APIEvents.bot_view}, "ctx": {"user": request.session.get('user_id'), "widget": True}})
    data = {"bot": bot, "user": await get_bot(bot_id, worker_session = request.app.state.worker_session)}
    bot_obj = await get_bot(bot_id)
    
    if not bot_obj or not data["user"]:
        return abort(404)

    if format == enums.WidgetFormat.json:
        return data
    elif format == enums.WidgetFormat.html:
        return await templates.TemplateResponse("widget.html", {"request": request} | data)
    elif format == enums.WidgetFormat.webp:
        widget_img = Image.new("RGBA", (300, 175), "black")
        async with aiohttp.ClientSession() as sess:
            async with sess.get(data["user"]["avatar"]) as res:
                avatar_img = await res.read()
            
        async with aiofiles.open("data/static/botlisticon.webp", mode='rb') as res:
            fates_img = await res.read()

        async with aiofiles.open("data/static/votes.png", mode='rb') as res:
            votes_img = await res.read()

        fates_pil = Image.open(io.BytesIO(fates_img)).resize((10, 10))
        votes_pil = Image.open(os.path.join('votes.png')).resize((15, 15))
        server_pil = Image.open(os.path.join('server.png')).resize((15, 15))
        avatar_pil = Image.open(io.BytesIO(avatar_img)).resize((100, 100))
        avatar_pil_bg = Image.new('RGBA', avatar_pil.size, (0,0,0))
            
        #pasting the bot image
        try:
            widget_img.paste(Image.alpha_composite(avatar_pil_bg, avatar_pil),(10,widget_img.size[-1]//8))
        except:
            widget_img.paste(avatar_pil,(10,widget_img.size[-1]//6))
            
        #pasting the fateslist logo
        try:
            widget_img.paste(Image.alpha_composite(avatar_pil_bg, fates_pil),(10,152))
        except:
            widget_img.paste(fates_pil,(10,152))
        
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
        
        font = os.path.join('LexendDeca-Regular.ttf')
        
        def get_font(string: str, d):
            font = os.path.join('LexendDeca-Regular.ttf')
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
            fill='white',
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
            fill='white',
            font=ImageFont.truetype(
                font,
                16,
                layout_engine=ImageFont.LAYOUT_RAQM
                )
            )
        
        #description
        if not bot.get('description'):
            return abort(404)
        wrapper = textwrap.TextWrapper(width=30)
        word_list = wrapper.wrap(text=bot['description'])
        d.text(
            (120,30), 
            str('\n'.join(word_list)), 
            fill='white',
            font=get_font(str(bot['description']),d)
        )
        
        #server count
        d.text(
            (140,96), 
            str(f'{bot["guild_count"]}'), 
            fill='white',
            font=get_font(str(bot["guild_count"]),d)
        )
        
        #votes
        d.text(
            (140,116),
            str(f'{bot["votes"]}'), 
            fill='white',
            font=get_font(str(bot['votes']),d)
        )
            

        def _stream():
            with io.BytesIO() as output:
                widget_img.save(output, format="WEBP")
                output.seek(0)
                yield from output

        return StreamingResponse(_stream(), media_type="image/webp")
            


@router.get(
    "/{bot_id}/raw",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=4)
            )
        )
    ]
)
async def get_raw_bot(request: Request, bot_id: int, bt: BackgroundTasks):
    """
    Gets the raw given to the template with a few differences (bot_id being string and not int and passing auth manually to the function (coming soon) as the API aims to be as stateless as possible)
    Note that you likely want the Get Bot API and not this in most cases
    This API is prone to change as render_bot will keep changing
    """
    return await render_bot(request, bt, bot_id, api = True)

@router.post(
    "/{bot_id}/stats", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            ) 
        ),
        Depends(bot_auth_check)
    ]
)
async def set_bot_stats(request: Request, bot_id: int, api: BotStats):
    """This endpoint allows you to set the guild + shard counts for your bot"""
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

@router.post(
    "/{bot_id}/appeal",
    response_model=APIResponse,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(bot_auth_check)
    ]
)
async def appeal_bot(request: Request, bot_id: int, data: BotAppeal):
    if len(data.appeal) < 7:
        return api_error(
            "Appeal must be at least 7 characters long"
        )
    client = request.app.state.worker_session.discord.main
    db = request.app.state.worker_session.postgres

    state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)

    if state == enums.BotState.denied:
        title = "Bot Resubmission"
        appeal_title = "Context"
    elif state == enums.BotState.banned:
        title = "Ban Appeal"
        appeal_title = "Appeal"
    else:
        return api_error(
            "You cannot send an appeal for a bot that is not banned or denied!"
        )
    await client.wait_until_ready()
    reschannel = client.get_channel(appeals_channel)
    resubmit_embed = discord.Embed(title=title, color=0x00ff00)
    bot = await get_bot(bot_id)
    resubmit_embed.add_field(name="Username", value = bot['username'])
    resubmit_embed.add_field(name="Bot ID", value = str(bot_id))
    resubmit_embed.add_field(name="Resubmission", value = str(state == enums.BotState.denied))
    resubmit_embed.add_field(name=appeal_title, value = data.appeal)
    await reschannel.send(embed = resubmit_embed)
    return api_success()
